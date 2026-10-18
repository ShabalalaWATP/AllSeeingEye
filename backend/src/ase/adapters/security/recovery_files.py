"""Protected local files with atomic replacement and a separate, fail-closed lock."""

import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from ase.domain.errors import Conflict


def _operator_uid() -> int:
    # Called only on POSIX; Windows Python deliberately has no geteuid attribute.
    return int(getattr(os, "geteuid")())  # noqa: B009 - absent from Windows type stubs


def safe_file(path: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts:
        raise Conflict("Recovery files require absolute paths without parent traversal.")
    if os.name == "nt" and (
        path.drive.startswith("\\\\")
        or any(":" in part or part.endswith((".", " ")) for part in path.parts[1:])
    ):
        raise Conflict(
            "Recovery files require ordinary local paths, without device or stream aliases."
        )
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise Conflict("Recovery paths cannot contain links or junctions.")
    if not path.parent.is_dir():
        raise Conflict("Create a private recovery directory before using it.")
    if os.name != "nt" and path.parent.stat().st_uid != _operator_uid():
        raise Conflict("Recovery directories must belong to the executing operator.")
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise Conflict("Recovery files must be ordinary, unlinked files.")
        if os.name != "nt" and info.st_uid != _operator_uid():
            raise Conflict("Recovery files must belong to the executing operator.")
        if os.name != "nt" and info.st_mode & 0o077:
            raise Conflict("Recovery files must be accessible only to their owner.")
    if os.name != "nt" and path.parent.stat().st_mode & 0o077:
        raise Conflict("Recovery directories must be accessible only to their owner.")
    # Compare canonical paths against exclusions, including Windows short-name aliases.
    return path.resolve()


def read_bounded(path: Path, limit: int) -> bytes:
    safe_file(path)
    with path.open("rb") as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise Conflict("Recovery file exceeds its safety limit.")
    return data


def _sync_directory(path: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def create_private(path: Path, data: bytes) -> None:
    safe_file(path)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as target:
        target.write(data)
        target.flush()
        os.fsync(target.fileno())
    _sync_directory(path.parent)


def replace_private(path: Path, data: bytes) -> None:
    safe_file(path)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        create_private(temporary, data)
        # The parent must be operator-owned; recheck links before replacement.
        safe_file(path)
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def journal_lock(path: Path) -> Iterator[None]:
    """Never steal a stale lock. Its existence requires operator investigation."""
    safe_file(path)
    try:
        create_private(path, b"Recovery journal operation in progress\n")
    except FileExistsError:
        raise Conflict("Recovery journal is locked; investigate before retrying.") from None
    try:
        yield
    finally:
        path.unlink()
        _sync_directory(path.parent)
