import json


def test_source_can_be_published_read_and_downloaded_with_cli(service, cli, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    content = b"%PDF-1.4\nfixed-reference\x00\xff\n"
    (a / "reference.pdf").write_bytes(content)
    result = cli(
        service,
        a,
        "publish",
        "source",
        "--file",
        "reference.pdf",
        "--title",
        "Reference",
        "--summary",
        "Fixed source",
        "--contributor",
        "Alice",
        "--key",
        "reference",
    )
    assert result.returncode == 0, result.stderr
    oid = json.loads(result.stdout)["id"]
    result = cli(service, b, "list", "sources")
    assert json.loads(result.stdout)[0]["id"] == oid
    result = cli(service, b, "show", "source", oid)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["title"] == "Reference"
    result = cli(service, b, "get", "source", oid, "--out", "reference.pdf")
    assert result.returncode == 0, result.stderr
    assert (b / "reference.pdf").read_bytes() == content


def test_complete_skill_preserves_relative_resources_empty_dirs_and_executes(
    service, cli, tmp_path
):
    import subprocess

    a, b = tmp_path / "a", tmp_path / "b"
    skill = a / "compute"
    for folder in ("scripts", "references", "assets", "templates", "empty"):
        (skill / folder).mkdir(parents=True, exist_ok=True)
    b.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: compute\ndescription: Compute fixed result.\n---\nRun scripts/compute.py.\n"
    )
    (skill / "references/method.txt").write_text("Add offset to all values.\n")
    (skill / "assets/offset.txt").write_text("3\n")
    (skill / "templates/result.txt").write_text("total={total}\n")
    (skill / "scripts/compute.py").write_text(
        "#!/usr/bin/env python3\nfrom pathlib import Path\n"
        "root = Path(__file__).resolve().parents[1]\n"
        'assert (root / "references/method.txt").read_text().startswith("Add")\n'
        'total = 2 + int((root / "assets/offset.txt").read_text())\n'
        'print((root / "templates/result.txt").read_text().format(total=total), end="")\n'
    )
    (skill / "scripts/compute.py").chmod(0o755)
    result = cli(
        service,
        a,
        "publish",
        "skill",
        "--dir",
        "compute",
        "--title",
        "Compute",
        "--summary",
        "Fixed computation",
        "--contributor",
        "Alice",
        "--key",
        "compute",
    )
    assert result.returncode == 0, result.stderr
    oid = json.loads(result.stdout)["id"]
    result = cli(service, b, "show", "skill", oid)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["title"] == "Compute"
    result = cli(service, b, "get", "skill", oid, "--out", "received")
    assert result.returncode == 0, result.stderr
    assert (b / "received/empty").is_dir()
    for path in skill.rglob("*"):
        remote = b / "received" / path.relative_to(skill)
        if path.is_file():
            assert remote.read_bytes() == path.read_bytes()
            assert bool(remote.stat().st_mode & 0o111) == bool(path.stat().st_mode & 0o111)
    completed = subprocess.run(
        [str(b / "received/scripts/compute.py")], cwd=b, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "total=5\n"
