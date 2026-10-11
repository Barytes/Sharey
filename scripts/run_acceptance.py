#!/usr/bin/env python3
"""Deterministic public-interface acceptance; deliberately not an Agent eval."""

import argparse
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/pilot-latency"


def run(out: Path) -> dict:
    out.mkdir(parents=True)
    out = out.resolve()
    a, b = out / "a", out / "b"
    shutil.copytree(FIXTURE, a)
    b.mkdir()
    token = secrets.token_urlsafe(32)
    config = out / "server.json"
    config.write_text(
        json.dumps(
            {
                "projects": {
                    "pilot": {
                        "goal": "Compare pilot latency; separate arithmetic from inference.",
                        "token": token,
                    }
                }
            }
        )
    )
    config.chmod(0o600)
    process = None
    server_log = (out / "server.log").open("ab")
    url = ""
    headers = {"Authorization": f"Bearer {token}"}

    def start():
        nonlocal process, url
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "sharey.cli",
                "serve",
                "--config",
                str(config),
                "--data-dir",
                str(out / "data"),
                "--port",
                str(port),
            ],
            cwd=out,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError((out / "server.log").read_text())
            try:
                if httpx.get(url + "/health", timeout=0.2).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.03)
        raise RuntimeError("Acceptance service did not become ready")

    def stop():
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)

    def cli(workspace: Path, *args: str) -> dict | list:
        env = {**os.environ, "SHAREY_URL": url, "SHAREY_PROJECT": "pilot", "SHAREY_TOKEN": token}
        completed = subprocess.run(
            [sys.executable, "-m", "sharey.cli", *args],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        with (out / "cli.jsonl").open("a") as log:
            log.write(
                json.dumps(
                    {
                        "workspace": workspace.name,
                        "args": args,
                        "exit": completed.returncode,
                        "stdout": completed.stdout,
                        "stderr": completed.stderr,
                    }
                )
                + "\n"
            )
        if completed.returncode:
            raise RuntimeError(f"CLI {args} failed: {completed.stderr}")
        return json.loads(completed.stdout)

    def node(
        workspace: Path,
        title: str,
        memory: str,
        parents: list[str],
        key: str,
        files: list[dict] | None = None,
    ) -> dict:
        (workspace / f"{key}.md").write_text(memory)
        manifest = {
            "schema_version": 1,
            "title": title,
            "summary": memory.splitlines()[0],
            "contributor": "Alice" if workspace == a else "Bob",
            "memory": f"{key}.md",
            "parents": parents,
            "sources": [ids["source"]],
            "skills": [ids["skill"]],
            "files": files or [],
        }
        (workspace / f"{key}.json").write_text(json.dumps(manifest))
        return cli(workspace, "publish", "node", "--manifest", f"{key}.json", "--key", key)

    ids: dict = {}
    try:
        start()
        ids["source"] = cli(
            a,
            "publish",
            "source",
            "--file",
            "protocol.md",
            "--title",
            "Pilot protocol",
            "--contributor",
            "Alice",
            "--key",
            "protocol",
        )["id"]
        ids["skill"] = cli(
            a,
            "publish",
            "skill",
            "--dir",
            "skill",
            "--title",
            "Pilot summarizer",
            "--summary",
            "Run all relative resources to summarize the fixed pilot.",
            "--contributor",
            "Alice",
            "--key",
            "summarizer",
        )["id"]
        ids["sharey_skill"] = cli(
            a,
            "publish",
            "skill",
            "--dir",
            str(ROOT / "skills/sharey"),
            "--title",
            "Sharey",
            "--contributor",
            "Alice",
            "--key",
            "sharey",
        )["id"]
        manifest = json.loads((a / "node-manifest.json").read_text())
        manifest.update(sources=[ids["source"]], skills=[ids["skill"]])
        (a / "node-manifest.json").write_text(json.dumps(manifest))
        root = cli(a, "publish", "node", "--manifest", "node-manifest.json", "--key", "root")
        ids["root"] = root["id"]
        view = cli(b, "overview")
        assert view["nodes"][0]["id"] == ids["root"]
        assert "pilot" in view["goal"]
        shown = cli(b, "show", "node", ids["root"])
        assert "not a randomized experiment" in shown["memory"]
        cli(b, "get", "node", ids["root"], "--out", "root")
        cli(b, "get", "source", ids["source"], "--out", "protocol.md")
        assert (b / "protocol.md").read_bytes() == (FIXTURE / "protocol.md").read_bytes()
        cli(b, "get", "skill", ids["skill"], "--out", "downloaded-skill")
        cli(b, "get", "skill", ids["sharey_skill"], "--out", "sharey-skill")
        for original in (FIXTURE / "skill").rglob("*"):
            if original.is_file():
                downloaded = b / "downloaded-skill" / original.relative_to(FIXTURE / "skill")
                assert downloaded.read_bytes() == original.read_bytes()
                assert bool(downloaded.stat().st_mode & 0o111) == bool(
                    original.stat().st_mode & 0o111
                )
        for original in (ROOT / "skills/sharey").rglob("*"):
            if original.is_file():
                assert (
                    b / "sharey-skill" / original.relative_to(ROOT / "skills/sharey")
                ).read_bytes() == original.read_bytes()
        executed = subprocess.run(
            [
                sys.executable,
                str(b / "downloaded-skill/scripts/summarize.py"),
                "--input",
                str(b / "root/files/pilot.csv"),
                "--out",
                str(b / "results"),
            ],
            cwd=b,
            capture_output=True,
            text=True,
            timeout=15,
        )
        (out / "skill-execution.json").write_text(
            json.dumps(
                {"exit": executed.returncode, "stdout": executed.stdout, "stderr": executed.stderr},
                indent=2,
            )
        )
        assert executed.returncode == 0, executed.stderr
        result = json.loads((b / "results/results.json").read_text())
        assert result == json.loads((FIXTURE / "expected-result.json").read_text())
        assert "collect randomized" in (b / "results/report.md").read_text()
        left = node(
            a,
            "Arithmetic check",
            "Means are 12 ms and 9 ms; difference is -3 ms.\nPilot arithmetic only.",
            [ids["root"]],
            "left",
        )
        right = node(
            b,
            "Measurement limitations",
            (
                "Three fixture trials per variant do not establish significance.\n"
                "Plan randomized repeated measurements."
            ),
            [ids["root"]],
            "right",
            [
                {"source": "results/results.json", "path": "results.json"},
                {"source": "results/report.md", "path": "report.md"},
            ],
        )
        ids.update(left=left["id"], right=right["id"])
        for parent in (ids["left"], ids["right"]):
            assert cli(b, "show", "node", parent)["parents"] == [ids["root"]]
        merged = node(
            b,
            "Combined pilot checkpoint",
            (
                "Arithmetic and limitations agree: a -3 ms pilot difference.\n"
                "Next: randomized repeat protocol; no significance claim."
            ),
            [ids["left"], ids["right"]],
            "merge",
        )
        ids["merge"] = merged["id"]
        expected_parents = {
            ids["root"]: [],
            ids["left"]: [ids["root"]],
            ids["right"]: [ids["root"]],
            ids["merge"]: [ids["left"], ids["right"]],
        }
        view = cli(b, "overview")
        assert {item["id"]: item["parents"] for item in view["nodes"]} == expected_parents
        for oid, parents in expected_parents.items():
            actual = subprocess.run(
                [
                    "git",
                    "--git-dir",
                    str(out / "data/pilot.git"),
                    "rev-list",
                    "--parents",
                    "-n",
                    "1",
                    oid,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            assert actual.stdout.split() == [oid, *parents]
        index = httpx.get(url + "/projects/pilot/index", headers=headers).text
        assert f"{ids['left']}, {ids['right']}" in index
        original_data = (FIXTURE / "work/pilot.csv").read_bytes()
        (a / "work/pilot.csv").write_text("changed locally\n")
        (a / "work/config.json").unlink()
        cli(b, "get", "file", ids["root"], "pilot.csv", "--out", "old-pilot.csv")
        assert (b / "old-pilot.csv").read_bytes() == original_data
        for item in view["nodes"]:
            cli(b, "get", "node", item["id"], "--out", "audit-" + item["id"])
        assert all(
            b"PRIVATE-CANARY" not in path.read_bytes()
            for folder in b.glob("audit-*")
            for path in folder.rglob("*")
            if path.is_file()
        )
        stop()
        start()
        assert cli(b, "overview") == view
        cli(b, "get", "node", ids["root"], "--out", "root-after-restart")
        assert (b / "root-after-restart/files/pilot.csv").read_bytes() == original_data
        assert cli(b, "publish", "node", "--manifest", "merge.json", "--key", "merge") == merged
        evidence = {
            "status": "passed",
            "interfaces": ["real HTTP", "CLI subprocess"],
            "publications": ids,
            "parents": expected_parents,
            "skill_result": result,
            "snapshot_unchanged": True,
            "private_canary_absent": True,
            "restart_preserved": True,
            "cross_vendor_agent_acceptance": "not exercised by this CLI runner",
        }
        (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        return evidence
    finally:
        stop()
        server_log.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, required=True, help="New directory for all evidence and workspaces"
    )
    args = parser.parse_args()
    print(json.dumps(run(args.out), indent=2))


if __name__ == "__main__":
    main()
