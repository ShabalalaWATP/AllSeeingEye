"""Shared admission and killable isolated execution of untrusted document imports."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import signal

# Only for CREATE_NO_WINDOW; execution uses fixed argv without a shell.
import subprocess  # nosec B404
import sys
import tempfile
import threading
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ase.adapters.research_imports.models import MAX_UPLOAD_BYTES, ExtractionResult, ImportRejected
from ase.adapters.research_imports.worker_protocol import validate_result

if TYPE_CHECKING:
    from ase.adapters.research_media.models import MediaExtractionResult, MediaTools

MAX_OUTPUT_BYTES = 1024 * 1024
MAX_MEDIA_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_SECONDS = 30.0
MAX_CONCURRENT = 2
CREATE_FLAGS = 0
if sys.platform == "win32":
    CREATE_FLAGS = subprocess.CREATE_NO_WINDOW


async def _spawn(directory: Path) -> asyncio.subprocess.Process:
    # Do not forward API keys, application settings or arbitrary Python startup
    # configuration. Isolated mode also excludes user site packages and cwd imports.
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL"}
    }
    # OCR/video helpers may allocate their own temporary workspaces. Keep those
    # under the parent's directory so abrupt worker termination cannot orphan raw media.
    environment.update({name: str(directory) for name in ("TEMP", "TMP", "TMPDIR")})
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-m",
        "ase.adapters.research_worker",
        cwd=directory,
        env=environment,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        creationflags=CREATE_FLAGS,
        start_new_session=os.name == "posix",
    )


def _kill_process_tree(process: asyncio.subprocess.Process) -> None:
    if os.name == "posix":
        with suppress(ProcessLookupError):
            # These APIs are absent from Windows Python/typeshed.
            getattr(os, "killpg")(process.pid, getattr(signal, "SIGKILL"))  # noqa: B009
    elif process.returncode is None:
        # The child owns a kill-on-close Job Object, so terminating the child also
        # closes its job and terminates any OCR/video subprocesses it created.
        process.kill()


async def _finish(process: asyncio.subprocess.Process) -> None:
    _kill_process_tree(process)
    await process.wait()


async def _settle[T](task: asyncio.Task[T]) -> tuple[T, bool]:
    interrupted = False
    while True:
        try:
            return await asyncio.shield(task), interrupted
        except asyncio.CancelledError:
            if task.cancelled():
                raise
            interrupted = True


class DocumentImportRunner:
    """Reuse one instance for process-local, immediate-rejection admission control."""

    def __init__(
        self, timeout: float = MAX_SECONDS, *, media_tools: MediaTools | None = None
    ) -> None:
        if not 0 < timeout <= MAX_SECONDS:
            raise ValueError("Document timeout must be greater than zero and at most 30 seconds.")
        self.timeout = timeout
        self.media_tools = media_tools
        self._active = 0
        self._lock = threading.Lock()

    async def run(self, data: bytes, filename: str) -> ExtractionResult:
        result = await self._admitted(data, filename, media=False)
        return cast(ExtractionResult, result)

    async def run_media(self, data: bytes, filename: str) -> MediaExtractionResult:
        """Use the same admission pool, with executable paths fixed by composition."""
        result = await self._admitted(data, filename, media=True)
        return cast("MediaExtractionResult", result)

    async def _admitted(
        self, data: bytes, filename: str, *, media: bool
    ) -> ExtractionResult | MediaExtractionResult:
        if not data or len(data) > MAX_UPLOAD_BYTES:
            raise ImportRejected("Upload is empty or exceeds the 8 MiB size limit.")
        if (
            not filename
            or len(filename) > 120
            or any(ord(char) < 32 for char in filename)
            or any(char in filename for char in "/\\:")
        ):
            raise ImportRejected("Use a plain filename of at most 120 characters.")
        with self._lock:
            if self._active >= MAX_CONCURRENT:
                raise ImportRejected(
                    "Document import is busy; retry when an active import finishes."
                )
            self._active += 1
        try:
            return await self._run(data, filename, media=media)
        finally:
            with self._lock:
                self._active -= 1

    async def _run(
        self, data: bytes, filename: str, *, media: bool
    ) -> ExtractionResult | MediaExtractionResult:
        with tempfile.TemporaryDirectory(prefix="ase-import-") as temporary:
            directory = Path(temporary)
            # These are bounded local writes, not parser work. Names are fixed and
            # independent of the operator's display filename.
            (directory / "input.bin").write_bytes(data)
            request: dict[str, object] = {
                "filename": filename,
                "mode": "media" if media else "document",
            }
            if media:
                request["tools"] = (
                    asdict(self.media_tools)
                    if self.media_tools is not None
                    else {"tesseract": None, "ffmpeg": None, "ffprobe": None}
                )
            (directory / "request.json").write_text(json.dumps(request), encoding="utf-8")
            process: asyncio.subprocess.Process | None = None
            spawn_task: asyncio.Task[asyncio.subprocess.Process] | None = None
            try:
                async with asyncio.timeout(self.timeout):
                    spawn_task = asyncio.create_task(_spawn(directory))
                    process = await asyncio.shield(spawn_task)
                    if await process.wait() != 0:
                        raise ImportRejected("Document parser exited without valid evidence.")
                    _kill_process_tree(process)
                    output = directory / "result.json"
                    if not output.is_file() or output.is_symlink():
                        raise ImportRejected("Document parser returned no evidence.")
                    maximum = MAX_MEDIA_OUTPUT_BYTES if media else MAX_OUTPUT_BYTES
                    with output.open("rb") as stream:
                        response = stream.read(maximum + 1)
                    if len(response) > maximum:
                        raise ImportRejected("Document parser output exceeded the size limit.")
                    if media:
                        from ase.adapters.research_media.worker_protocol import (  # noqa: PLC0415
                            validate_media_result,
                        )

                        return validate_media_result(
                            response, filename, hashlib.sha256(data).hexdigest()
                        )
                    return validate_result(response, filename, hashlib.sha256(data).hexdigest())
            except TimeoutError:
                raise ImportRejected("Document extraction exceeded its time limit.") from None
            except OSError:
                raise ImportRejected("Document parser could not run safely.") from None
            finally:
                interrupted = False
                if process is None and spawn_task is not None:
                    # Cancellation can arrive while the OS is starting the child.
                    # Retain that task so its eventual process is still reaped.
                    with suppress(OSError):
                        process, interrupted = await _settle(spawn_task)
                if process is not None:
                    _, cleanup_interrupted = await _settle(asyncio.create_task(_finish(process)))
                    interrupted = interrupted or cleanup_interrupted
                if interrupted:
                    raise asyncio.CancelledError


_shared_runner = DocumentImportRunner()


async def run_document_import(data: bytes, filename: str) -> ExtractionResult:
    """Import with the shared two-process admission limit and a 30-second deadline."""
    return await _shared_runner.run(data, filename)
