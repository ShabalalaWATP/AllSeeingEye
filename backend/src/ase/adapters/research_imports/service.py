"""Networkless Unix-socket service owning the constrained parser subprocesses."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import struct
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from ase.adapters.research_imports.models import MAX_UPLOAD_BYTES
from ase.adapters.research_imports.remote import MAX_HEADER_BYTES, PARSER_SOCKET
from ase.adapters.research_imports.runner import DocumentImportRunner
from ase.adapters.research_media.models import MediaTools
from ase.adapters.research_media.worker_protocol import MAX_RESPONSE_BYTES, encode_media_result

ERROR = b'{"ok":false,"error":"rejected"}'
READ_TIMEOUT_SECONDS = 5.0


def _header(data: bytes) -> tuple[str, bool, int]:
    value = json.loads(data)
    if not isinstance(value, dict) or set(value) != {"filename", "media", "size"}:
        raise ValueError
    filename, media, size = value["filename"], value["media"], value["size"]
    if not isinstance(filename, str) or type(media) is not bool or type(size) is not int:
        raise ValueError
    if not 1 <= size <= MAX_UPLOAD_BYTES:
        raise ValueError
    return filename, media, size


def _encode(result: Any, media: bool) -> bytes:
    value = encode_media_result(result) if media else {"ok": True, "result": asdict(result)}
    data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    maximum = MAX_RESPONSE_BYTES if media else 1024 * 1024
    return data if len(data) <= maximum else ERROR


async def _client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, runner: DocumentImportRunner
) -> None:
    response = ERROR
    try:
        async with asyncio.timeout(READ_TIMEOUT_SECONDS):
            header_size = struct.unpack(">I", await reader.readexactly(4))[0]
            if not 1 <= header_size <= MAX_HEADER_BYTES:
                raise ValueError
            filename, media, size = _header(await reader.readexactly(header_size))
            data = await reader.readexactly(size)
        result = await (runner.run_media(data, filename) if media else runner.run(data, filename))
        response = _encode(result, media)
    except Exception:
        response = ERROR
    try:
        writer.write(struct.pack(">I", len(response)) + response)
        await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()
        with suppress(OSError):
            await writer.wait_closed()


async def start_server(
    socket_path: Path = PARSER_SOCKET, runner: DocumentImportRunner | None = None
) -> asyncio.AbstractServer:
    socket_path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    with suppress(FileNotFoundError):
        socket_path.unlink()
    service_runner = runner or DocumentImportRunner(
        media_tools=MediaTools(
            tesseract=shutil.which("tesseract"),
            ffmpeg=shutil.which("ffmpeg"),
            ffprobe=shutil.which("ffprobe"),
        )
    )
    start_unix = cast(
        Callable[..., Awaitable[asyncio.AbstractServer]],
        vars(asyncio)["start_unix_server"],
    )
    server = await start_unix(
        lambda reader, writer: _client(reader, writer, service_runner),
        path=str(socket_path),
    )
    os.chmod(socket_path, 0o600)
    return server


async def main() -> None:
    server = await start_server()
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
