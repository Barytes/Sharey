import io
import lzma
import stat
import unicodedata
import zipfile
import zlib
from pathlib import PurePosixPath

from sharey.errors import ShareyError


def relative_path(path: str) -> str:
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or ":" in path
        or any(part in ("", ".", "..") for part in path.split("/"))
        or any(ord(char) < 32 or ord(char) == 127 for char in path)
    ):
        raise ValueError("Expected a normalized relative path")
    return str(PurePosixPath(path))


def encode(files: dict[str, tuple[bytes, bool]], directories: list[str] | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directories or []):
            info = zipfile.ZipInfo(relative_path(path) + "/")
            info.create_system = 3
            info.external_attr = (stat.S_IFDIR | 0o755) << 16
            archive.writestr(info, b"")
        for path, (data, executable) in sorted(files.items()):
            info = zipfile.ZipInfo(relative_path(path))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return output.getvalue()


def decode(
    content: bytes, max_bytes: int = 16 * 1024 * 1024, max_entries: int = 1000
) -> tuple[dict[str, tuple[bytes, bool]], list[str]]:
    files: dict[str, tuple[bytes, bool]] = {}
    directories: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if len(archive.infolist()) > max_entries:
                raise ShareyError(413, "Archive entry limit exceeded")
            if sum(info.file_size for info in archive.infolist()) > max_bytes:
                raise ShareyError(413, "Unpacked byte limit exceeded")
            seen: set[str] = set()
            aliases: dict[str, str] = {}
            entries = []
            for info in archive.infolist():
                path = relative_path(
                    info.orig_filename[:-1] if info.is_dir() else info.orig_filename
                )
                mode = info.external_attr >> 16
                file_type = stat.S_IFMT(mode)
                if file_type not in (0, stat.S_IFDIR if info.is_dir() else stat.S_IFREG):
                    raise ValueError("Archive accepts only regular files and directories")
                if path in seen:
                    raise ValueError("Duplicate archive path")
                for component in [PurePosixPath(path), *PurePosixPath(path).parents]:
                    original = component.as_posix()
                    normalized = unicodedata.normalize("NFC", original).casefold()
                    if normalized in aliases and aliases[normalized] != original:
                        raise ValueError("Archive paths have case or Unicode aliases")
                    aliases[normalized] = original
                seen.add(path)
                entries.append((path, info))
            file_paths = {path for path, info in entries if not info.is_dir()}
            for path, info in entries:
                if any(parent.as_posix() in file_paths for parent in PurePosixPath(path).parents):
                    raise ValueError("File and directory path conflict")
                if info.is_dir():
                    if info.file_size:
                        raise ValueError("Directory entry contains file data")
                    directories.append(path)
                else:
                    with archive.open(info) as source:
                        data = source.read(max_bytes + 1)
                    if len(data) > max_bytes:
                        raise ShareyError(413, "Unpacked byte limit exceeded")
                    files[path] = (data, bool(info.external_attr >> 16 & 0o111))
    except (
        zipfile.BadZipFile,
        RuntimeError,
        NotImplementedError,
        zlib.error,
        lzma.LZMAError,
        OSError,
        EOFError,
    ) as error:
        raise ValueError("Invalid ZIP archive") from error
    return files, directories
