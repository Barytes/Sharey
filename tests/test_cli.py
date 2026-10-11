import json

import httpx
import pytest


def test_cli_reads_real_http_project_and_lists_objects(service, cli, tmp_path):
    result = cli(service, tmp_path, "overview")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "project": "demo",
        "goal": "Compare measurements",
        "nodes": [],
        "sources": [],
        "skills": [],
    }
    for kind in ("nodes", "sources", "skills"):
        result = cli(service, tmp_path, "list", kind)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == []
    denied = cli(service, tmp_path, "overview", token="wrong")
    assert denied.returncode != 0
    assert "401" in denied.stderr
    assert "Compare measurements" not in denied.stderr


def test_cli_publishes_selected_disk_snapshot_and_downloads_after_local_deletion(
    service, cli, tmp_path
):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "memory.md").write_text("# Goal\nTwo observations only.\n")
    (a / "data.bin").write_bytes(b"\x00\xffselected\n")
    (a / "run.sh").write_bytes(b"#!/bin/sh\nprintf ok\n")
    (a / "run.sh").chmod(0o755)
    (a / "private.txt").write_text("PRIVATE-CANARY")
    manifest = {
        "schema_version": 1,
        "title": "Selected snapshot",
        "summary": "Two observations.",
        "contributor": "Alice",
        "memory": "memory.md",
        "parents": [],
        "sources": [],
        "skills": [],
        "files": [
            {"source": "data.bin", "path": "nested/data.bin"},
            {"source": "run.sh", "path": "run.sh"},
        ],
    }
    (a / "publish.json").write_text(json.dumps(manifest))
    result = cli(service, a, "publish", "node", "--manifest", "publish.json", "--key", "snapshot")
    assert result.returncode == 0, result.stderr
    oid = json.loads(result.stdout)["id"]
    (a / "data.bin").unlink()
    (a / "memory.md").write_text("changed")
    result = cli(service, b, "show", "node", oid)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["memory"] == "# Goal\nTwo observations only.\n"
    result = cli(service, b, "get", "file", oid, "nested/data.bin", "--out", "raw.bin")
    assert result.returncode == 0, result.stderr
    assert (b / "raw.bin").read_bytes() == b"\x00\xffselected\n"
    result = cli(service, b, "get", "node", oid, "--out", "snapshot")
    assert result.returncode == 0, result.stderr
    assert (b / "snapshot/files/nested/data.bin").read_bytes() == b"\x00\xffselected\n"
    assert (b / "snapshot/memory.md").read_text() == "# Goal\nTwo observations only.\n"
    assert (b / "snapshot/files/run.sh").stat().st_mode & 0o111
    assert sorted(p.name for p in (b / "snapshot").iterdir()) == [
        "files",
        "memory.md",
        "metadata.json",
    ]
    duplicate = cli(service, b, "get", "node", oid, "--out", "snapshot")
    assert duplicate.returncode != 0
    assert "exists" in duplicate.stderr.lower()
    duplicate = cli(service, b, "get", "file", oid, "nested/data.bin", "--out", "raw.bin")
    assert duplicate.returncode != 0
    assert (b / "raw.bin").read_bytes() == b"\x00\xffselected\n"


def test_single_file_download_restores_selected_execution_mark(service, cli, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "memory.md").write_text("Runnable helper")
    (work / "helper.sh").write_text("#!/bin/sh\nprintf hello\n")
    (work / "helper.sh").chmod(0o755)
    (work / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Helper",
                "summary": "",
                "contributor": "Alice",
                "memory": "memory.md",
                "files": [{"source": "helper.sh", "path": "helper.sh"}],
            }
        )
    )
    result = cli(service, work, "publish", "node", "--manifest", "manifest.json", "--key", "helper")
    assert result.returncode == 0, result.stderr
    oid = json.loads(result.stdout)["id"]
    result = cli(service, work, "get", "file", oid, "helper.sh", "--out", "received.sh")
    assert result.returncode == 0, result.stderr
    assert (work / "received.sh").read_bytes() == b"#!/bin/sh\nprintf hello\n"
    assert (work / "received.sh").stat().st_mode & 0o111


@pytest.mark.parametrize("case", ["implicit-directories", "configured-size"])
def test_cli_downloads_every_accepted_snapshot(service, cli, tmp_path, case):
    from test_nodes import node_bundle

    if case == "implicit-directories":
        files = {f"files/d{number}/f.txt": str(number).encode() for number in range(500)}
    else:
        service.stop()
        config = json.loads(service.config.read_text())
        config["limits"] = {
            "max_upload_bytes": 32 * 1024 * 1024,
            "max_unpacked_bytes": 32 * 1024 * 1024,
        }
        service.config.write_text(json.dumps(config))
        service.start()
        files = {"files/large.bin": b"x" * (17 * 1024 * 1024)}
    response = httpx.post(
        service.url + "/projects/demo/nodes",
        headers={
            "Authorization": "Bearer demo-secret",
            "Content-Type": "application/zip",
            "Idempotency-Key": "accepted-snapshot",
        },
        content=node_bundle(files=files),
        timeout=60,
    )
    assert response.status_code == 201, response.text
    result = cli(service, tmp_path, "get", "node", response.json()["id"], "--out", "received")
    assert result.returncode == 0, result.stderr
    for path, content in files.items():
        assert (tmp_path / "received" / path).read_bytes() == content
    assert (tmp_path / "received/memory.md").read_bytes() == b"# Goal\nCompare measurements.\n"
