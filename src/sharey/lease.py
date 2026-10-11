import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def storage_lease(root: Path, projects: dict) -> Iterator[None]:
    """One service owns a data directory, so leftover Git locks are recoverable."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / ".sharey.lock").open("a+b") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(
                "Sharey data directory is already in use by another service"
            ) from error
        try:
            for project in projects:
                repo = root / f"{project}.git"
                for lock in (repo / "refs/sharey").rglob("*.lock"):
                    lock.unlink()
                (repo / "config.lock").unlink(missing_ok=True)
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
