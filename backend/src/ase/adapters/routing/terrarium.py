"""Fixed-origin Terrarium tiles, bounded decoded cache and coalesced downloads."""

import asyncio
import struct
import zlib
from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.secret_urls import SecretFeedUrl
from ase.domain.events import Point
from ase.domain.terrain import TERRAIN_ZOOM, TILE_SIZE, TileCoordinate, terrain_pixel

TERRAIN_ORIGIN = "https://s3.amazonaws.com"
TERRAIN_TILE_BYTES = 512 * 1024
CACHE_TILES = 128
# Cached RGB buffers are exactly 196,608 bytes each, at most 24 MiB plus small keys.
RGB_BYTES = TILE_SIZE * TILE_SIZE * 3


def _validate_header(data: bytes) -> None:
    width, height, depth, colour, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", data
    )
    if (width, height) != (256, 256) or depth != 8 or colour not in (2, 6):
        raise ValueError("Unsupported terrain pixel encoding")
    if compression != 0 or filtering != 0 or interlace not in (0, 1):
        raise ValueError("Unsupported terrain compression")


def _image_bytes(payload: bytes) -> bytes:
    """Discard ancillary PNG metadata before Pillow can decompress text profiles."""
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Unsupported terrain image")
    output = bytearray(payload[:8])
    offset = 8
    header = False
    while offset + 12 <= len(payload):
        length = int.from_bytes(payload[offset : offset + 4], "big")
        end = offset + length + 12
        if end > len(payload):
            raise ValueError("Truncated terrain PNG")
        kind = payload[offset + 4 : offset + 8]
        data = payload[offset + 8 : end - 4]
        checksum = int.from_bytes(payload[end - 4 : end], "big")
        if zlib.crc32(kind + data) != checksum:
            raise ValueError("Corrupt terrain PNG")
        if kind == b"IHDR":
            if header or offset != 8 or length != 13:
                raise ValueError("Invalid terrain PNG header")
            _validate_header(data)
            header = True
        if not header or kind == b"tRNS":
            raise ValueError("Unsupported terrain transparency or header")
        if kind in {b"IHDR", b"IDAT", b"IEND"}:
            output.extend(payload[offset:end])
        elif not kind[0] & 32:
            raise ValueError("Unsupported critical terrain PNG chunk")
        if kind == b"IEND":
            if length or end != len(payload):
                raise ValueError("Invalid terrain PNG end")
            return bytes(output)
        offset = end
    raise ValueError("Incomplete terrain PNG")


def decode_terrarium(payload: bytes) -> bytes:
    if not payload or len(payload) > TERRAIN_TILE_BYTES:
        raise ValueError("Terrain tile exceeds its byte limit")
    with Image.open(BytesIO(_image_bytes(payload)), formats=("PNG",)) as image:
        if image.size != (TILE_SIZE, TILE_SIZE) or image.mode not in {"RGB", "RGBA"}:
            raise ValueError("Unsupported terrain tile dimensions or encoding")
        image.load()
        if image.mode == "RGBA" and image.getchannel("A").getextrema() != (255, 255):
            raise ValueError("Terrain tile contains transparent missing data")
        return image.convert("RGB").tobytes()


def sample_terrarium(pixels: bytes, x: int, y: int) -> float:
    if len(pixels) != RGB_BYTES or not 0 <= x < TILE_SIZE or not 0 <= y < TILE_SIZE:
        raise ValueError("Invalid terrain pixel")
    offset = (y * TILE_SIZE + x) * 3
    red, green, blue = pixels[offset : offset + 3]
    elevation = red * 256 + green + blue / 256 - 32768
    # Preserve below-sea-level terrain and bathymetry. Reject void/sentinel pixels.
    if not -12000 <= elevation <= 10000:
        raise ValueError("Missing or implausible terrain height")
    return elevation


@dataclass
class _Pending:
    task: asyncio.Task[bytes]
    waiters: int = 0


class TerrariumGateway:
    def __init__(self, http: FeedHttpClient) -> None:
        self._http = http
        self._cache: OrderedDict[TileCoordinate, bytes] = OrderedDict()
        self._pending: dict[TileCoordinate, _Pending] = {}
        self._downloads = asyncio.Semaphore(4)

    async def _load(self, tile: TileCoordinate) -> bytes:
        async with self._downloads:
            x, y = tile
            target = SecretFeedUrl(
                TERRAIN_ORIGIN,
                f"{TERRAIN_ORIGIN}/elevation-tiles-prod/terrarium/{TERRAIN_ZOOM}/{x}/{y}.png",
            )
            payload = await self._http.get_secret_bytes(target)
            # Decoding is bounded to 256² pixels and four workers, away from the API loop.
            work = asyncio.create_task(asyncio.to_thread(decode_terrarium, payload))
            try:
                decoded = await asyncio.shield(work)
            except asyncio.CancelledError:
                await asyncio.gather(work, return_exceptions=True)
                raise
            self._cache[tile] = decoded
            self._cache.move_to_end(tile)
            while len(self._cache) > CACHE_TILES:
                self._cache.popitem(last=False)
            return decoded

    async def _tile(self, tile: TileCoordinate) -> bytes:
        cached = self._cache.get(tile)
        if cached is not None:
            self._cache.move_to_end(tile)
            return cached
        pending = self._pending.get(tile)
        if pending is None:
            pending = _Pending(asyncio.create_task(self._load(tile)))
            self._pending[tile] = pending
        pending.waiters += 1
        try:
            return await asyncio.shield(pending.task)
        finally:
            pending.waiters -= 1
            if pending.waiters == 0:
                self._pending.pop(tile, None)
                if not pending.task.done():
                    pending.task.cancel()
                await asyncio.gather(pending.task, return_exceptions=True)

    async def elevations(self, positions: tuple[Point, ...]) -> tuple[float, ...]:
        pixels = [terrain_pixel(point) for point in positions]
        async with asyncio.TaskGroup() as group:
            tasks = {tile: group.create_task(self._tile(tile)) for tile in {p[0] for p in pixels}}
        return tuple(sample_terrarium(tasks[tile].result(), x, y) for tile, x, y in pixels)

    async def aclose(self) -> None:
        pending = [entry.task for entry in self._pending.values()]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        self._pending.clear()
        self._cache.clear()
