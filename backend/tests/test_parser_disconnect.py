"""Socket abandonment cancels only its own work and waits for admission cleanup."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from ase.adapters.research_imports import extract_upload
from ase.adapters.research_imports.remote import RemoteDocumentImportRunner
from ase.adapters.research_imports.runner import DocumentImportRunner
from ase.adapters.research_imports.service import _client, start_server


class BlockingRunner(DocumentImportRunner):
    def __init__(self) -> None:
        super().__init__()
        self.started = {name: asyncio.Event() for name in ("first.txt", "second.txt", "third.txt")}
        self.release = {name: asyncio.Event() for name in self.started}
        self.cancelled = asyncio.Event()
        self.cleanup = asyncio.Event()
        self.cleaned = asyncio.Event()
        self.directories: dict[str, Path] = {}

    async def _run(self, data: bytes, filename: str, *, media: bool):
        with tempfile.TemporaryDirectory() as directory:
            self.directories[filename] = Path(directory)
            try:
                self.started[filename].set()
                await self.release[filename].wait()
                return extract_upload(data, filename)
            except asyncio.CancelledError:
                self.cancelled.set()
                await self.cleanup.wait()
                raise
            finally:
                if filename == "first.txt":
                    asyncio.get_running_loop().call_soon(self.cleaned.set)


@pytest.mark.parametrize("media", [False, True])
async def test_disconnect_waits_for_cleanup_and_cannot_cancel_another_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, media: bool
) -> None:
    runner = BlockingRunner()
    # Windows asyncio lacks Unix streams. Exercise identical transport lifecycle
    # over TCP there, and real Unix-domain sockets in Linux CI.
    socket_path = tmp_path / "parser.sock"
    if os.name == "nt":
        server = await asyncio.start_server(lambda r, w: _client(r, w, runner), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async def connect(_: str):
            return await asyncio.open_connection("127.0.0.1", port)

        monkeypatch.setattr(asyncio, "open_unix_connection", connect, raising=False)
    else:
        server = await start_server(socket_path, runner)
    client = RemoteDocumentImportRunner(socket_path)
    first = asyncio.create_task(
        client.run_media(b"first", "first.txt") if media else client.run(b"first", "first.txt")
    )
    second = asyncio.create_task(client.run(b"second", "second.txt"))
    try:
        async with asyncio.timeout(5):
            await runner.started["first.txt"].wait()
            await runner.started["second.txt"].wait()
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            await runner.cancelled.wait()
            assert runner._active == 2
            assert runner.directories["first.txt"].exists()
            assert not second.done()
            runner.cleanup.set()
            await runner.cleaned.wait()
            assert runner._active == 1
            assert not runner.directories["first.txt"].exists()
            assert not second.done()
            runner.release["third.txt"].set()
            third = await client.run(b"third", "third.txt")
            assert third.units[0].text == "third"
            runner.release["second.txt"].set()
            assert (await second).units[0].text == "second"
            assert runner._active == 0
    finally:
        runner.cleanup.set()
        for task in (first, second):
            task.cancel()
        await asyncio.gather(first, second, return_exceptions=True)
        server.close()
        await server.wait_closed()
