"""Selected local files and explicit download destinations."""

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from sharey.archives import decode, encode, relative_path
from sharey.models import NodeManifest


def open_local(path: Path, flags: int) -> int:
    """Walk using directory descriptors so links cannot redirect selected reads."""
    absolute = Path(os.path.abspath(path))
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return os.open(absolute.name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    finally:
        os.close(descriptor)


def read_regular(path: Path) -> tuple[bytes, bool]:
    with os.fdopen(open_local(path, os.O_RDONLY), "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Selection accepts only regular files")
        content = source.read()
        after = os.fstat(source.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("Selected file changed while being read; retry with stable files")
        return content, bool(before.st_mode & 0o111)


def provenance(source: Path, declared_source: str, path: str, entry: tuple[bytes, bool]) -> dict:
    data, executable = entry
    result: dict = {
        "path": path,
        "source_path": declared_source if not Path(declared_source).is_absolute() else source.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "git": None,
    }
    binary = shutil.which("git")
    if not binary:
        return result
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        {"GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    )

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [binary, "--literal-pathspecs", "-C", str(source.parent), *args],
            env=env,
            capture_output=True,
        )

    root = git("rev-parse", "--show-toplevel")
    baseline = git("rev-parse", "--verify", "HEAD")
    if root.returncode or baseline.returncode:
        return result
    commit = baseline.stdout.decode().strip()
    relative = Path(os.path.abspath(source)).relative_to(root.stdout.decode().strip()).as_posix()
    tree = git("ls-tree", "--full-tree", "-z", commit, "--", relative)
    origin = {"commit": commit, "path": relative, "state": "untracked"}
    if tree.stdout:
        mode, _, blob = tree.stdout.split(b"\t", 1)[0].decode().split()
        previous = git("cat-file", "blob", blob)
        origin["state"] = (
            "clean"
            if not previous.returncode
            and previous.stdout == data
            and (mode == "100755") == executable
            else "modified"
        )
    result["git"] = origin
    return result


def pack_node(manifest: Path) -> bytes:
    try:
        spec = NodeManifest.model_validate_json(read_regular(manifest)[0]).model_dump()
    except ValueError as error:
        raise ValueError("Invalid node manifest") from error
    base = manifest.parent
    memory = read_regular(base / spec.pop("memory"))[0]
    files = {"memory.md": (memory, False)}
    origins = []
    for selected in spec.pop("files"):
        source = base / selected["source"]
        path = "files/" + relative_path(selected["path"])
        if path in files:
            raise ValueError("Duplicate selected destination")
        files[path] = read_regular(source)
        origins.append(provenance(source, selected["source"], selected["path"], files[path]))
    spec["provenance"] = origins
    files["metadata.json"] = (json.dumps(spec, ensure_ascii=False).encode(), False)
    return encode(files)


def pack_source(source: Path, title: str, summary: str, contributor: str) -> bytes:
    metadata = {
        "schema_version": 1,
        "title": title,
        "summary": summary,
        "contributor": contributor,
        "filename": source.name,
    }
    return encode(
        {
            "metadata.json": (json.dumps(metadata).encode(), False),
            "files/" + relative_path(source.name): read_regular(source),
        }
    )


def pack_skill(directory: Path, title: str, summary: str, contributor: str) -> bytes:
    os.close(open_local(directory, os.O_RDONLY | os.O_DIRECTORY))
    metadata = {"schema_version": 1, "title": title, "summary": summary, "contributor": contributor}
    files = {"metadata.json": (json.dumps(metadata).encode(), False)}
    directories = []
    for path in sorted(directory.rglob("*")):
        mode = path.lstat().st_mode
        name = "skill/" + relative_path(path.relative_to(directory).as_posix())
        if stat.S_ISDIR(mode):
            directories.append(name)
        elif stat.S_ISREG(mode):
            files[name] = read_regular(path)
        else:
            raise ValueError("Skill accepts only regular files and directories")
    if "skill/SKILL.md" not in files:
        raise ValueError("Skill directory must contain SKILL.md")
    return encode(files, directories)


def save_file(out: Path, content: bytes, executable: bool = False) -> None:
    with out.open("xb") as target:
        target.write(content)
        os.fchmod(target.fileno(), 0o755 if executable else 0o644)


def save_archive(out: Path, content: bytes) -> None:
    if out.exists() or out.is_symlink():
        raise ValueError(f"Destination exists: {out}")
    files, directories = decode(content)
    with tempfile.TemporaryDirectory(prefix=".sharey-", dir=out.parent) as temporary:
        stage = Path(temporary) / "content"
        stage.mkdir()
        for name in directories:
            (stage / name).mkdir(parents=True, exist_ok=True)
        for name, (data, executable) in files.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o755 if executable else 0o644)
        out.mkdir()
        try:
            os.replace(stage, out)
        except OSError:
            out.rmdir()
            raise
