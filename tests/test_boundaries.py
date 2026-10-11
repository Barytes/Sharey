import io
import json
import stat
import warnings
import zipfile

import pytest
from conftest import AUTH
from test_nodes import node_bundle, publish


def unsafe_bundle(name, mode=stat.S_IFREG | 0o644, duplicate=False):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "metadata.json",
            json.dumps(
                {
                    "schema_version": 1,
                    "title": "Unsafe",
                    "summary": "",
                    "contributor": "Alice",
                    "parents": [],
                    "sources": [],
                    "skills": [],
                }
            ),
        )
        archive.writestr("memory.md", "Memory")
        info = zipfile.ZipInfo(name)
        info.create_system = 3
        info.external_attr = mode << 16
        archive.writestr(info, "PRIVATE-CANARY")
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(info, "replacement")
    return output.getvalue()


@pytest.mark.parametrize(
    "name,mode,duplicate",
    [
        ("/absolute", stat.S_IFREG | 0o644, False),
        ("files/../escape", stat.S_IFREG | 0o644, False),
        ("files/a//b", stat.S_IFREG | 0o644, False),
        ("files/./b", stat.S_IFREG | 0o644, False),
        ("files/a\\b", stat.S_IFREG | 0o644, False),
        ("files/C:/escape", stat.S_IFREG | 0o644, False),
        ("files/a\x7fb", stat.S_IFREG | 0o644, False),
        ("files/link", stat.S_IFLNK | 0o777, False),
        ("files/fifo", stat.S_IFIFO | 0o644, False),
        ("files/duplicate", stat.S_IFREG | 0o644, True),
    ],
)
def test_unsafe_uploads_never_become_visible(api, name, mode, duplicate):
    before = api.get("/projects/demo/overview", headers=AUTH).json()
    response = publish(api, unsafe_bundle(name, mode, duplicate), key="unsafe")
    assert response.status_code == 422, response.text
    assert api.get("/projects/demo/overview", headers=AUTH).json() == before


def test_incomplete_invalid_and_conflicting_publications_are_rejected(api):
    from test_nodes import bundle

    node_meta = {"schema_version": 1, "title": "Invalid", "summary": "", "contributor": "Alice"}
    cases = [
        ("nodes", b"not a zip"),
        ("nodes", bundle(node_meta, {"files/a": b"x"})),
        ("nodes", bundle({**node_meta, "schema_version": 2}, {"memory.md": b"memory"})),
        ("nodes", bundle({**node_meta, "unexpected": "secret"}, {"memory.md": b"memory"})),
        ("nodes", bundle(node_meta, {"memory.md": b"\xff"})),
        ("nodes", bundle(node_meta, {"memory.md": b"memory", "private.txt": b"canary"})),
        ("nodes", bundle(node_meta, {"memory.md": b"memory", "files/a": b"x", "files/a/b": b"y"})),
        ("skills", bundle(node_meta, {"skill/scripts/run.py": b"print(1)"})),
        ("skills", bundle(node_meta, {"skill/SKILL.md": b"# Method", "private.txt": b"canary"})),
        (
            "sources",
            bundle({**node_meta, "filename": "ref"}, {"files/ref": b"a", "files/other": b"b"}),
        ),
    ]
    for number, (kind, content) in enumerate(cases):
        response = publish(api, content, kind=kind, key=f"invalid-{number}")
        assert response.status_code == 422, response.text
        assert api.get("/projects/demo/overview", headers=AUTH).json()["nodes"] == []
        assert api.get("/projects/demo/sources", headers=AUTH).json() == []
        assert api.get("/projects/demo/skills", headers=AUTH).json() == []


@pytest.mark.parametrize(
    "compression,corrupt_offset",
    [(zipfile.ZIP_DEFLATED, 0), (zipfile.ZIP_BZIP2, 0), (zipfile.ZIP_LZMA, 4)],
)
def test_corrupt_compressed_upload_returns_validation_json_without_publication(
    api, compression, corrupt_offset
):
    import struct

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        archive.writestr("metadata.json", b"{}")
        archive.writestr("memory.md", b"Memory")
    damaged = bytearray(output.getvalue())
    name_size, extra_size = struct.unpack_from("<HH", damaged, 26)
    damaged[30 + name_size + extra_size + corrupt_offset] = (
        0x07 if compression == zipfile.ZIP_DEFLATED else 0xFF
    )  # Invalid DEFLATE block, BZIP2 header, or LZMA properties.
    response = publish(api, bytes(damaged), key="corrupt-deflate")
    assert response.status_code == 422, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Invalid publication archive"}
    assert api.get("/projects/demo/nodes", headers=AUTH).json() == []


@pytest.mark.parametrize(
    "limit,content",
    [
        ({"max_upload_bytes": 50}, node_bundle()),
        ({"max_unpacked_bytes": 50}, node_bundle()),
        ({"max_entries": 2}, node_bundle()),
    ],
)
def test_configured_upload_limits_reject_without_publication(tmp_path, limit, content):
    from conftest import CONFIG
    from fastapi.testclient import TestClient

    from sharey.server import create_app

    with TestClient(create_app(tmp_path / "limited", {**CONFIG, "limits": limit})) as client:
        response = publish(client, content)
        assert response.status_code == 413, response.text
        assert client.get("/projects/demo/nodes", headers=AUTH).json() == []


@pytest.mark.parametrize("selected", ["link", "linked-parent", "fifo", "duplicate"])
def test_cli_rejects_ambiguous_or_nonregular_selected_files(service, cli, tmp_path, selected):
    import os

    work = tmp_path / "work"
    work.mkdir()
    (work / "memory.md").write_text("Research memory")
    (work / "private.txt").write_text("PRIVATE-CANARY")
    (work / "dir").mkdir()
    (work / "dir/data.txt").write_text("PRIVATE-CANARY")
    (work / "link").symlink_to("private.txt")
    (work / "linked-parent").symlink_to("dir", target_is_directory=True)
    os.mkfifo(work / "fifo")
    source = "linked-parent/data.txt" if selected == "linked-parent" else selected
    files = [{"source": source, "path": "data.txt"}]
    if selected == "duplicate":
        files = [{"source": "private.txt", "path": "same"}, {"source": "memory.md", "path": "same"}]
    (work / "publish.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Unsafe selection",
                "summary": "",
                "contributor": "Alice",
                "memory": "memory.md",
                "files": files,
            }
        )
    )
    result = cli(service, work, "publish", "node", "--manifest", "publish.json", "--key", "unsafe")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert json.loads(cli(service, work, "list", "nodes").stdout) == []
    assert (work / "private.txt").read_text() == "PRIVATE-CANARY"


def test_dirty_and_untracked_publication_preserves_original_git_and_truthful_provenance(
    service, cli, tmp_path
):
    import hashlib
    import subprocess

    work = tmp_path / "research"
    work.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(work), *args], capture_output=True, check=True
        ).stdout

    git("init")
    git("config", "user.name", "Researcher")
    git("config", "user.email", "researcher@example.invalid")
    git("remote", "add", "origin", "https://secret-token@example.invalid/private/research.git")
    (work / "tracked.txt").write_bytes(b"baseline\n")
    git("add", "tracked.txt")
    git("commit", "-m", "baseline")
    baseline = git("rev-parse", "HEAD").decode().strip()
    (work / "tracked.txt").write_bytes(b"dirty-current\n")
    (work / "untracked.bin").write_bytes(b"\x00untracked\xff")
    (work / "private.txt").write_bytes(b"PRIVATE-CANARY")
    (work / ".gitignore").write_text("untracked.bin\n")
    (work / "memory.md").write_text("Explicit memory; no chat history.")
    (work / "publish.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Current work",
                "summary": "Dirty and untracked.",
                "contributor": "Alice",
                "memory": "memory.md",
                "files": [
                    {"source": "tracked.txt", "path": "tracked.txt"},
                    {"source": "untracked.bin", "path": "untracked.bin"},
                ],
            }
        )
    )
    before = {
        path.relative_to(work).as_posix(): path.read_bytes()
        for path in work.rglob("*")
        if path.is_file()
    }
    result = cli(service, work, "publish", "node", "--manifest", "publish.json", "--key", "dirty")
    assert result.returncode == 0, result.stderr
    after = {
        path.relative_to(work).as_posix(): path.read_bytes()
        for path in work.rglob("*")
        if path.is_file()
    }
    assert before == after
    metadata = json.loads(result.stdout)
    assert metadata["parents"] == []
    assert {entry["path"] for entry in metadata["files"]} == {"tracked.txt", "untracked.bin"}
    provenance = {entry["path"]: entry for entry in metadata["provenance"]}
    assert provenance["tracked.txt"]["sha256"] == hashlib.sha256(b"dirty-current\n").hexdigest()
    assert provenance["tracked.txt"]["git"] == {
        "commit": baseline,
        "path": "tracked.txt",
        "state": "modified",
    }
    assert provenance["untracked.bin"]["git"] == {
        "commit": baseline,
        "path": "untracked.bin",
        "state": "untracked",
    }
    assert "secret-token" not in result.stdout
    assert "PRIVATE-CANARY" not in result.stdout
    read = cli(
        service, work, "get", "file", metadata["id"], "tracked.txt", "--out", "retrieved.txt"
    )
    assert read.returncode == 0, read.stderr
    assert (work / "retrieved.txt").read_bytes() == b"dirty-current\n"


@pytest.mark.parametrize(
    "name,mode,duplicate",
    [
        ("link", stat.S_IFLNK | 0o777, False),
        ("repeat", stat.S_IFREG | 0o644, True),
        ("../escape", stat.S_IFREG | 0o644, False),
    ],
)
def test_cli_validates_download_archive_before_writing(
    service, cli, tmp_path, name, mode, duplicate
):
    import http.server
    import threading
    from types import SimpleNamespace

    content = unsafe_bundle(name, mode, duplicate)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    fake_service = SimpleNamespace(url=f"http://127.0.0.1:{server.server_port}")
    try:
        result = cli(fake_service, tmp_path, "get", "skill", "f" * 40, "--out", "received")
        assert result.returncode != 0
        assert "Traceback" not in result.stderr
        assert not (tmp_path / "received").exists()
        assert not (tmp_path / "escape").exists()
        assert list(tmp_path.glob(".sharey-*")) == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_client_without_git_publishes_explicit_files_and_keeps_private_content_local(
    service, cli, tmp_path
):
    work = tmp_path / "nogit"
    work.mkdir()
    (work / "memory.md").write_text("Explicit shared memory.")
    (work / "selected.bin").write_bytes(b"\x00current\xff")
    (work / "private.txt").write_text("PRIVATE-CANARY")
    (work / "publish.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "No Git required",
                "summary": "",
                "contributor": "Alice",
                "memory": "memory.md",
                "files": [{"source": "selected.bin", "path": "selected.bin"}],
            }
        )
    )
    result = cli(
        service,
        work,
        "publish",
        "node",
        "--manifest",
        "publish.json",
        "--key",
        "nogit",
        extra_env={"PATH": "/nonexistent"},
    )
    assert result.returncode == 0, result.stderr
    metadata = json.loads(result.stdout)
    assert metadata["provenance"][0]["git"] is None
    result = cli(
        service,
        work,
        "get",
        "node",
        metadata["id"],
        "--out",
        "download",
        extra_env={"PATH": "/nonexistent"},
    )
    assert result.returncode == 0, result.stderr
    assert (work / "download/files/selected.bin").read_bytes() == b"\x00current\xff"
    assert not (work / ".git").exists()
    assert not (work / "download/files/private.txt").exists()
    assert b"PRIVATE-CANARY" not in b"".join(
        path.read_bytes() for path in (work / "download").rglob("*") if path.is_file()
    )


def test_invalid_request_key_content_type_and_configuration_fail_cleanly(api, tmp_path):
    from sharey.server import create_app

    for key in ("", "x" * 129, "bad key"):
        response = publish(api, node_bundle(), key=key)
        assert response.status_code == 422
    response = api.post(
        "/projects/demo/nodes",
        content=node_bundle(),
        headers={**AUTH, "Idempotency-Key": "valid", "Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    with pytest.raises(ValueError):
        create_app(
            tmp_path / "data2", {"projects": {"../escaped": {"goal": "Goal", "token": "secret"}}}
        )
    assert not (tmp_path / "escaped.git").exists()


def test_provenance_tracks_nested_clean_files_against_correct_git_base(service, cli, tmp_path):
    import subprocess

    work = tmp_path / "nested-repo"
    (work / "code").mkdir(parents=True)

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(work), *args], capture_output=True, check=True
        ).stdout

    git("init")
    git("config", "user.name", "Researcher")
    git("config", "user.email", "researcher@example.invalid")
    (work / "code/clean.py").write_text("print(1)\n")
    git("add", "code/clean.py")
    git("commit", "-m", "nested baseline")
    (work / "memory.md").write_text("Nested source provenance.")
    (work / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Nested source",
                "summary": "",
                "contributor": "Alice",
                "memory": "memory.md",
                "files": [{"source": "code/clean.py", "path": "code/clean.py"}],
            }
        )
    )
    result = cli(service, work, "publish", "node", "--manifest", "manifest.json", "--key", "nested")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["provenance"][0]["git"] == {
        "commit": git("rev-parse", "HEAD").decode().strip(),
        "path": "code/clean.py",
        "state": "clean",
    }


def test_case_or_unicode_aliases_cannot_overwrite_downloaded_files_or_cross_projects(api, tmp_path):
    from test_nodes import bundle

    from sharey.server import create_app

    metadata = {
        "schema_version": 1,
        "title": "Aliased paths",
        "summary": "",
        "contributor": "Alice",
    }
    for paths in (
        {"files/A": b"a", "files/a": b"b"},
        {"files/A/x": b"a", "files/a/y": b"b"},
        {"files/é": b"a", "files/e\u0301": b"b"},
    ):
        response = publish(api, bundle(metadata, {"memory.md": b"memory", **paths}))
        assert response.status_code == 422
        assert api.get("/projects/demo/nodes", headers=AUTH).json() == []
    with pytest.raises(ValueError):
        create_app(
            tmp_path / "aliases",
            {
                "projects": {
                    "demo": {"goal": "First", "token": "one"},
                    "Demo": {"goal": "Second", "token": "two"},
                }
            },
        )
