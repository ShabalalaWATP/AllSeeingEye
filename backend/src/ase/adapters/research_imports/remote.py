"""Bounded Unix-socket client for the separately constrained parser service."""

from __future__ import annotations

import asyncio
import hashlib
import json
import struct
from collections.abc import Awaitable, Callable
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ase.adapters.research_imports.models import MAX_UPLOAD_BYTES, ExtractionResult, ImportRejected
from ase.adapters.research_imports.worker_protocol import validate_result
from ase.adapters.research_media.worker_protocol import MAX_RESPONSE_BYTES, validate_media_result

if TYPE_CHECKING:
    from ase.adapters.research_media.models import MediaExtractionResult

PARSER_SOCKET = Path("/run/ase-parser/parser.sock")
MAX_HEADER_BYTES = 512
REQUEST_TIMEOUT_SECONDS = 35.0


def _request(data: bytes, filename: str, media: bool) -> bytes:
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ImportRejected("Upload is empty or exceeds the 8 MiB size limit.")
    if (
        not filename
        or len(filename) > 120
        or any(ord(char) < 32 for char in filename)
        or any(char in filename for char in "/\\:")
    ):
        raise ImportRejected("Use a plain filename of at most 120 characters.")
    header = json.dumps(
        {"filename": filename, "media": media, "size": len(data)},
        separators=(",", ":"),
    ).encode("utf-8")
    if len(header) > MAX_HEADER_BYTES:
        raise ImportRejected("The parser request is invalid.")
    return struct.pack(">I", len(header)) + header + data


class RemoteDocumentImportRunner:
    """Send uploads to the networkless parser cgroup and revalidate every result."""

    def __init__(self, socket_path: Path = PARSER_SOCKET) -> None:
        self.socket_path = socket_path

    async def run(self, data: bytes, filename: str) -> ExtractionResult:
        response = await self._exchange(data, filename, media=False)
        return validate_result(response, filename, hashlib.sha256(data).hexdigest())

    async def run_media(self, data: bytes, filename: str) -> MediaExtractionResult:
        response = await self._exchange(data, filename, media=True)
        return validate_media_result(response, filename, hashlib.sha256(data).hexdigest())

    async def _exchange(self, data: bytes, filename: str, *, media: bool) -> bytes:
        writer: asyncio.StreamWriter | None = None
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                open_unix = cast(
                    Callable[[str], Awaitable[tuple[asyncio.StreamReader, asyncio.StreamWriter]]],
                    vars(asyncio)["open_unix_connection"],
                )
                reader, writer = await open_unix(str(self.socket_path))
                writer.write(_request(data, filename, media))
                await writer.drain()
                size = struct.unpack(">I", await reader.readexactly(4))[0]
                maximum = MAX_RESPONSE_BYTES if media else 1024 * 1024
                if not 1 <= size <= maximum:
                    raise ImportRejected("Document parser returned invalid evidence.")
                return await reader.readexactly(size)
        except ImportRejected:
            raise
        except (AttributeError, OSError, TimeoutError, asyncio.IncompleteReadError, struct.error):
            raise ImportRejected("Document parser could not run safely.") from None
        finally:
            if writer is not None:
                writer.close()
                with suppress(OSError):
                    await writer.wait_closed()
