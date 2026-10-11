"""Git objects and create-only publication refs; no checkout or shared index."""

import hashlib
import json
import os
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from sharey.archives import encode
from sharey.errors import ShareyError
from sharey.faults import pause_for_test


class GitStore:
    def __init__(self, root: Path, projects: dict):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.publication_locks = {project: threading.Lock() for project in projects}
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_AUTHOR_NAME": "Sharey",
                "GIT_AUTHOR_EMAIL": "sharey@localhost",
                "GIT_COMMITTER_NAME": "Sharey",
                "GIT_COMMITTER_EMAIL": "sharey@localhost",
            }
        )
        for project in projects:
            repo = self.repo(project)
            if not (repo / "HEAD").exists():
                subprocess.run(
                    ["git", "init", "--bare", "--object-format=sha1", str(repo)],
                    env=self.env,
                    check=True,
                    capture_output=True,
                )

    def repo(self, project: str) -> Path:
        return self.root / f"{project}.git"

    def git(self, project: str, *args: str, content: bytes | None = None) -> bytes:
        result = subprocess.run(
            ["git", "--git-dir", str(self.repo(project)), *args],
            input=content,
            env=self.env,
            capture_output=True,
        )
        if result.returncode:
            raise ShareyError(500, "Git storage operation failed")
        return result.stdout

    def ids(self, project: str, kind: str) -> list[str]:
        return (
            self.git(project, "for-each-ref", "--format=%(objectname)", f"refs/sharey/{kind}/")
            .decode()
            .splitlines()
        )

    def require(self, project: str, kind: str, oid: str) -> None:
        if oid not in self.ids(project, kind):
            raise ShareyError(404, "Published object not found")

    def entries(self, project: str, oid: str) -> dict[str, tuple[str, str]]:
        output = self.git(project, "ls-tree", "-r", "-t", "-z", oid)
        result = {}
        for entry in output.split(b"\0"):
            if not entry:
                continue
            header, name = entry.split(b"\t", 1)
            mode, _, blob = header.decode().split()
            result[name.decode()] = (mode, blob)
        return result

    def blob(self, project: str, oid: str, path: str) -> bytes:
        entry = self.entries(project, oid).get(path)
        if entry is None or entry[0] == "040000":
            raise ShareyError(404, "Published file not found")
        return self.git(project, "cat-file", "blob", entry[1])

    def describe(self, project: str, kind: str, oid: str) -> dict:
        self.require(project, kind, oid)
        metadata = json.loads(self.blob(project, oid, "metadata.json"))
        metadata.pop("request_hash", None)
        metadata["id"] = oid
        metadata["parents"] = self.git(project, "show", "-s", "--format=%P", oid).decode().split()
        files = []
        for path, (mode, blob) in self.entries(project, oid).items():
            prefix = "skill/" if kind == "skills" else "files/"
            if path.startswith(prefix) and mode != "040000":
                size = int(self.git(project, "cat-file", "-s", blob))
                files.append(
                    {"path": path[len(prefix) :], "size": size, "executable": mode == "100755"}
                )
        metadata["files"] = files
        return metadata

    def listing(self, project: str, kind: str) -> list[dict]:
        return sorted(
            [self.describe(project, kind, oid) for oid in self.ids(project, kind)],
            key=lambda item: (item["created_at"], item["id"]),
        )

    def archive(self, project: str, kind: str, oid: str) -> bytes:
        metadata = self.describe(project, kind, oid)
        files = {}
        directories = []
        for path, (mode, blob) in self.entries(project, oid).items():
            if kind == "skills":
                if not path.startswith("skill/"):
                    continue
                path = path[6:]
            if mode == "040000":
                directories.append(path)
            else:
                files[path] = (self.git(project, "cat-file", "blob", blob), mode == "100755")
        if kind != "skills":
            files["metadata.json"] = (json.dumps(metadata, ensure_ascii=False).encode(), False)
        return encode(files, directories)

    def tree(
        self, project: str, files: dict[str, tuple[bytes, bool]], directories: list[str], key: str
    ) -> str:
        root: dict = {}
        for path in directories:
            current = root
            for part in path.split("/"):
                current = current.setdefault(part, {})
        for path, entry in files.items():
            parts = path.split("/")
            current = root
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = entry

        def write_tree(directory: dict) -> str:
            entries = []
            for name, value in sorted(directory.items()):
                if isinstance(value, dict):
                    mode, kind, oid = "040000", "tree", write_tree(value)
                else:
                    data, executable = value
                    oid = (
                        self.git(project, "hash-object", "-w", "--stdin", content=data)
                        .decode()
                        .strip()
                    )
                    pause_for_test("during-objects", key)
                    mode, kind = ("100755" if executable else "100644"), "blob"
                entries.append(f"{mode} {kind} {oid}\t{name}".encode() + b"\0")
            return self.git(project, "mktree", "-z", content=b"".join(entries)).decode().strip()

        return write_tree(root)

    def publish(
        self,
        project: str,
        kind: str,
        key: str,
        metadata: dict,
        files: dict[str, tuple[bytes, bool]],
        directories: list[str] | None = None,
    ) -> dict:
        ref = f"refs/sharey/{kind}/{hashlib.sha256(key.encode()).hexdigest()}"
        canonical_directories = set(directories or [])
        for path in [*files, *canonical_directories]:
            canonical_directories.update(
                parent.as_posix()
                for parent in PurePosixPath(path).parents
                if parent.as_posix() != "."
            )
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "metadata": metadata,
                    "directories": sorted(canonical_directories),
                    "files": [
                        {
                            "path": path,
                            "sha256": hashlib.sha256(data).hexdigest(),
                            "executable": executable,
                        }
                        for path, (data, executable) in sorted(files.items())
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

        def replay() -> dict | None:
            existing = (
                self.git(project, "for-each-ref", "--format=%(objectname)", ref).decode().strip()
            )
            if existing:
                saved = json.loads(self.blob(project, existing, "metadata.json"))
                if saved["request_hash"] != fingerprint:
                    raise ShareyError(409, "Idempotency-Key already used with different content")
                return self.describe(project, kind, existing)
            return None

        previous = replay()
        if previous is not None:
            return previous
        if kind == "nodes":
            for field, referenced_kind in (
                ("parents", "nodes"),
                ("sources", "sources"),
                ("skills", "skills"),
            ):
                references = metadata.get(field, [])
                if len(references) != len(set(references)):
                    raise ShareyError(422, f"Duplicate {field} reference")
                published = set(self.ids(project, referenced_kind))
                if any(reference not in published for reference in references):
                    raise ShareyError(422, f"Invalid {field} reference")
        metadata = {
            **metadata,
            "kind": kind,
            "created_at": datetime.now(UTC).isoformat(),
            "request_hash": fingerprint,
        }
        files = {**files, "metadata.json": (json.dumps(metadata, sort_keys=True).encode(), False)}
        tree = self.tree(project, files, sorted(canonical_directories), key)
        parents = [
            argument for parent in metadata.get("parents", []) for argument in ("-p", parent)
        ]
        oid = (
            self.git(project, "commit-tree", tree, *parents, content=b"Sharey publication\n")
            .decode()
            .strip()
        )
        pause_for_test("before-ref", key)
        with self.publication_locks[project]:
            previous = replay()
            if previous is not None:
                return previous
            self.git(project, "update-ref", ref, oid, "0" * 40)
        pause_for_test("after-ref", key)
        return self.describe(project, kind, oid)
