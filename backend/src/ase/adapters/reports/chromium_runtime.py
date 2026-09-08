"""Explicit Linux deployment policy, never inferred from a desktop browser install."""

import hashlib
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from ase.adapters.reports.render_cgroup import RenderCgroup
from ase.domain.errors import InvalidRequest


def immutable_path(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    for item in (resolved, *resolved.parents):
        info = item.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise InvalidRequest("The renderer runtime must be owned and writable only by root.")
    return resolved


def immutable_rootfs(root: Path) -> Path:
    resolved = immutable_path(root)
    if not resolved.is_dir() or resolved == Path("/"):
        raise InvalidRequest("A dedicated immutable renderer filesystem is required.")
    for index, entry in enumerate(resolved.rglob("*")):
        if index >= 20_000 or not entry.resolve(strict=True).is_relative_to(resolved):
            raise InvalidRequest("Invalid renderer filesystem boundary.")
        immutable_path(entry)
    return resolved


def verified_file(path: Path, digest: str) -> Path:
    resolved = immutable_path(path)
    info = resolved.stat()
    if (
        len(digest) != 64
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid != 0
        or info.st_mode & 0o022
    ):
        raise InvalidRequest("The pinned renderer executable is unavailable.")
    with resolved.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != digest:
        raise InvalidRequest("The pinned renderer executable failed verification.")
    return resolved


@dataclass(frozen=True)
class LinuxChromiumPolicy:
    rootfs: Path
    browser: str
    browser_sha256: str
    bubblewrap: Path
    bubblewrap_sha256: str
    cgroup_root: Path

    def prepare(self, directory: Path) -> RenderCgroup:
        if sys.platform != "linux":
            raise InvalidRequest("The isolated PDF runtime requires configured Linux isolation.")
        root = immutable_rootfs(self.rootfs)
        if not root.is_dir() or root.stat().st_uid != 0 or root.stat().st_mode & 0o022:
            raise InvalidRequest("A root-owned immutable renderer filesystem is required.")
        browser = Path(self.browser)
        if not browser.is_absolute() or ".." in browser.parts:
            raise InvalidRequest("Invalid pinned renderer path.")
        executable = (root / browser.relative_to("/")).resolve(strict=True)
        if not executable.is_relative_to(root):
            raise InvalidRequest("Renderer executable escapes its filesystem.")
        verified_file(executable, self.browser_sha256)
        if not (root / "usr/bin/python3").resolve(strict=True).is_relative_to(root):
            raise InvalidRequest("The isolated Python runtime is unavailable.")
        verified_file(self.bubblewrap, self.bubblewrap_sha256)
        if directory.resolve() != directory or directory.stat().st_uid != os.geteuid():
            raise InvalidRequest("Invalid private renderer directory.")
        return RenderCgroup.create(self.cgroup_root)

    def command(self, directory: Path) -> list[str]:
        return [
            str(self.bubblewrap.resolve()),
            "--unshare-user",
            "--unshare-pid",
            "--unshare-net",
            "--unshare-ipc",
            "--unshare-uts",
            "--die-with-parent",
            "--new-session",
            "--ro-bind",
            str(self.rootfs.resolve()),
            "/",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--size",
            str(64 * 1024 * 1024),
            "--tmpfs",
            "/tmp",  # noqa: S108  # A private tmpfs inside the new mount namespace.
            "--size",
            str(64 * 1024 * 1024),
            "--tmpfs",
            "/work",
            "--ro-bind",
            str(directory / "input.html"),
            "/work/input.html",
            "--chdir",
            "/work",
            "--clearenv",
            "--setenv",
            "HOME",
            "/work/profile",
            "--setenv",
            "LANG",
            "C.UTF-8",
            "--",
            "/usr/bin/python3",
            "-I",
            "-m",
            "ase.adapters.reports.chromium_pdf_child",
            self.browser,
        ]
