"""Operate only on newly owned children of an already delegated cgroup v2 tree."""

import asyncio
import os
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path

from ase.domain.errors import InvalidRequest

MEMORY_BYTES = 1024 * 1024 * 1024
MAX_PIDS = 128


def owned_directory(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    info = resolved.stat()
    if (
        info.st_mode & 0o022
        or path.is_symlink()
        or not stat.S_ISDIR(info.st_mode)
        or info.st_uid != getattr(os, "geteuid")()  # noqa: B009
    ):
        raise InvalidRequest("The delegated renderer resource boundary is unavailable.")
    return resolved


@dataclass(frozen=True)
class RenderCgroup:
    root: Path
    path: Path

    def control(self, name: str) -> Path:
        if name not in {
            "memory.max",
            "memory.swap.max",
            "pids.max",
            "cgroup.procs",
            "cgroup.kill",
            "cgroup.events",
        }:
            raise InvalidRequest("Invalid renderer resource control.")
        path = owned_directory(self.path)
        if path.parent != self.root or not path.name.startswith("ase-render-"):
            raise InvalidRequest("Invalid renderer resource boundary.")
        target = path / name
        if target.is_symlink() or target.resolve(strict=True).parent != path:
            raise InvalidRequest("Invalid renderer resource control.")
        return target

    @classmethod
    def create(cls, root: Path) -> "RenderCgroup":
        resolved = owned_directory(root)
        mount = Path("/sys/fs/cgroup").resolve(strict=True)
        if resolved == mount or not resolved.is_relative_to(mount):
            raise InvalidRequest("A delegated cgroup v2 subtree is required.")
        enabled = (resolved / "cgroup.subtree_control").read_text().split()
        if not {"memory", "pids"}.issubset(enabled):
            raise InvalidRequest("Delegated memory and process controllers are required.")
        path = resolved / ("ase-render-" + uuid.uuid4().hex)
        path.mkdir(mode=0o700)
        job = cls(resolved, path)
        try:
            job.control("memory.max").write_text(str(MEMORY_BYTES))
            job.control("memory.swap.max").write_text("0")
            job.control("pids.max").write_text(str(MAX_PIDS))
            job.control("cgroup.kill")
            return job
        except BaseException:
            path.rmdir()  # No process has been admitted; never remove recursively.
            raise

    async def close(self) -> None:
        self.control("cgroup.kill").write_text("1")
        for _ in range(100):
            if "populated 0" in self.control("cgroup.events").read_text().splitlines():
                owned_directory(self.path)
                self.path.rmdir()
                return
            await asyncio.sleep(0.05)
        raise InvalidRequest("Renderer cleanup did not complete; runtime is unavailable.")
