"""Bounded cancellable Chromium export, with independently supplied OS isolation."""

import asyncio
import json
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

from ase.adapters.reports.chromium_pdf_child import MAX_PAGES, MAX_PDF_BYTES
from ase.adapters.reports.chromium_runtime import LinuxChromiumPolicy
from ase.adapters.reports.print_html import render_print_html
from ase.adapters.reports.render_cgroup import RenderCgroup
from ase.application.ports.report_export import RenderCleanupFailed
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import ReportDocument

MAX_SECONDS = 60.0
CREATE_FLAGS = 0
if sys.platform == "win32":
    CREATE_FLAGS = subprocess.CREATE_NO_WINDOW


async def _settle[T](task: asyncio.Task[T]) -> tuple[T, bool]:
    interrupted = False
    while True:
        try:
            return await asyncio.shield(task), interrupted
        except asyncio.CancelledError:
            if task.cancelled():
                raise
            interrupted = True


async def _spawn(directory: Path) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-m",
        "ase.adapters.reports.chromium_worker",
        cwd=directory,
        env={"LANG": "C.UTF-8"},
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        creationflags=CREATE_FLAGS,
    )


async def _render_html(document: ReportDocument) -> bytes:
    task = asyncio.create_task(asyncio.to_thread(render_print_html, document))
    html, was_cancelled = await _settle(task)
    if was_cancelled:
        raise asyncio.CancelledError
    return html


class ChromiumPdfWorker:
    def __init__(self, policy: LinuxChromiumPolicy, *, timeout: float = MAX_SECONDS) -> None:
        if not 0 < timeout <= MAX_SECONDS:
            raise ValueError("Invalid PDF render deadline")
        self.policy, self.timeout, self.unhealthy = policy, timeout, False

    async def render(self, document: ReportDocument) -> bytes:
        if self.unhealthy:
            raise InvalidRequest("The isolated PDF runtime requires operator recovery.")
        html = await _render_html(document)
        directory = Path(tempfile.mkdtemp(prefix="ase-pdf-")).resolve()
        try:
            job: RenderCgroup | None = None
            process: asyncio.subprocess.Process | None = None
            spawn: asyncio.Task[asyncio.subprocess.Process] | None = None
            try:
                async with asyncio.timeout(self.timeout):
                    preparing = asyncio.create_task(
                        asyncio.to_thread(self.policy.prepare, directory)
                    )
                    job, was_cancelled = await _settle(preparing)
                    if was_cancelled:
                        raise asyncio.CancelledError
                    if job is None:
                        raise InvalidRequest(
                            "The isolated renderer resource boundary is unavailable."
                        )
                    (directory / "input.html").write_bytes(html)
                    request = {
                        "command": self.policy.command(directory),
                        "cgroup": str(job.path),
                        "cgroup_root": str(job.root),
                    }
                    (directory / "request.json").write_text(json.dumps(request))
                    spawn = asyncio.create_task(_spawn(directory))
                    process = await asyncio.shield(spawn)
                    if process.stdout is None:
                        raise ValueError("Missing renderer transport")
                    result = await self._result(process.stdout)
                    if await process.wait() != 0:
                        raise InvalidRequest("The isolated PDF renderer could not complete.")
                    return result
            except TimeoutError:
                raise InvalidRequest("The isolated PDF renderer exceeded its deadline.") from None
            except (OSError, ValueError, KeyError, TypeError):
                raise InvalidRequest(
                    "The isolated PDF renderer is unavailable or returned invalid output."
                ) from None
            finally:
                await self._cleanup(process, spawn, job)
        finally:
            # Preserve bounded private input for operator recovery if descendants may live.
            if not self.unhealthy:
                parent = Path(tempfile.gettempdir()).resolve()
                if directory.parent != parent or not directory.name.startswith("ase-pdf-"):
                    raise InvalidRequest("Invalid renderer cleanup boundary.")
                if directory.is_symlink() or directory.resolve() != directory:
                    raise InvalidRequest("Invalid renderer cleanup boundary.")
                shutil.rmtree(directory)

    async def _cleanup(
        self,
        process: asyncio.subprocess.Process | None,
        spawn: asyncio.Task[asyncio.subprocess.Process] | None,
        job: RenderCgroup | None,
    ) -> None:
        interrupted = False
        if process is None and spawn is not None:
            with suppress(OSError):
                process, interrupted = await _settle(spawn)
        try:
            if job is not None:
                _, stopped = await _settle(asyncio.create_task(job.close()))
                interrupted = interrupted or stopped
        except Exception:
            self.unhealthy = True
            raise RenderCleanupFailed(
                "The isolated PDF runtime requires operator recovery."
            ) from None
        finally:
            if process is not None:
                if process.returncode is None:
                    with suppress(ProcessLookupError):
                        process.kill()
                try:
                    _, stopped = await _settle(asyncio.create_task(self._reap(process)))
                    interrupted = interrupted or stopped
                except TimeoutError:
                    self.unhealthy = True
                    raise RenderCleanupFailed(
                        "The isolated PDF runtime requires operator recovery."
                    ) from None
        if interrupted:
            raise asyncio.CancelledError

    @staticmethod
    async def _reap(process: asyncio.subprocess.Process) -> None:
        # Drain discarded output so a paused pipe cannot prevent subprocess reaping.
        # Unverified inherited pipes quarantine admission instead of waiting forever.
        async with asyncio.timeout(5):
            if process.stdout is not None:
                while await process.stdout.read(64 * 1024):
                    pass
            await process.wait()

    @staticmethod
    async def _result(stream: asyncio.StreamReader) -> bytes:
        raw = await stream.readline()
        if len(raw) > 1024 or not raw.endswith(b"\n"):
            raise ValueError("Invalid renderer receipt")
        receipt = json.loads(raw)
        if not isinstance(receipt, dict) or set(receipt) != {"pages", "bytes"}:
            raise ValueError("Invalid renderer receipt")
        if type(receipt["pages"]) is not int or not 1 <= receipt["pages"] <= MAX_PAGES:
            raise ValueError("Invalid renderer page count")
        size = receipt["bytes"]
        if type(size) is not int or not 5 <= size <= MAX_PDF_BYTES:
            raise ValueError("Invalid renderer PDF size")
        try:
            data = await stream.readexactly(size)
        except asyncio.IncompleteReadError:
            raise ValueError("Incomplete renderer PDF") from None
        if not data.startswith(b"%PDF-") or await stream.read(1):
            raise ValueError("Invalid renderer PDF bytes")
        return data
