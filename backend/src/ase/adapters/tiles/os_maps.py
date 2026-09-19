"""Ordnance Survey raster tiles fetched with the server-side key and cached in memory.

The OS Data Hub free plan allows 600 transactions a minute per API; a bounded
least-recently-used cache keeps repeated views of the same area from spending them.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict

import httpx

from ase.adapters.feeds.secret_urls import protect_http_logs
from ase.application.ports import RateLimiter
from ase.application.ports.tiles import Tile, TileUpstreamError

UPSTREAM = "https://api.os.uk/maps/raster/v1/zxy/{layer}/{z}/{x}/{y}.png"
DEFAULT_CACHE_BYTES = 64 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_TILE_BYTES = 1024 * 1024
GLOBAL_REQUESTS_PER_MINUTE = 540
MAX_CONCURRENT_REQUESTS = 8


class TileCache:
    """LRU cache bounded by total bytes rather than entry count (tiles vary in size)."""

    def __init__(self, max_bytes: int = DEFAULT_CACHE_BYTES) -> None:
        self._max_bytes = max_bytes
        self._bytes = 0
        self._items: OrderedDict[str, Tile] = OrderedDict()

    def get(self, key: str) -> Tile | None:
        tile = self._items.get(key)
        if tile is not None:
            self._items.move_to_end(key)
        return tile

    def put(self, key: str, tile: Tile) -> None:
        size = len(tile.content)
        if size > self._max_bytes:
            return
        if key in self._items:
            self._bytes -= len(self._items.pop(key).content)
        self._items[key] = tile
        self._bytes += size
        while self._bytes > self._max_bytes:
            _, evicted = self._items.popitem(last=False)
            self._bytes -= len(evicted.content)

    @property
    def bytes(self) -> int:
        return self._bytes

    def __len__(self) -> int:
        return len(self._items)


class OsMapsTileProvider:
    def __init__(
        self,
        key: str,
        *,
        client: httpx.AsyncClient | None = None,
        cache: TileCache | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self._key = key
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(DEFAULT_TIMEOUT_SECONDS))
        self._cache = cache or TileCache()
        self._limiter = limiter
        self._admission = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self._inflight_lock = asyncio.Lock()
        self._inflight: dict[str, asyncio.Task[Tile]] = {}

    @property
    def configured(self) -> bool:
        return True

    async def fetch(self, layer: str, z: int, x: int, y: int) -> Tile:
        cache_key = f"{layer}/{z}/{x}/{y}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        async with self._inflight_lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
            task = self._inflight.get(cache_key)
            if task is None:
                task = asyncio.create_task(self._fetch_uncached(cache_key, layer, z, x, y))
                self._inflight[cache_key] = task
        return await asyncio.shield(task)

    async def _fetch_uncached(self, cache_key: str, layer: str, z: int, x: int, y: int) -> Tile:
        url = UPSTREAM.format(layer=layer, z=z, x=x, y=y)
        try:
            if self._limiter is not None:
                retry = self._limiter.hit("os-maps:global", GLOBAL_REQUESTS_PER_MINUTE, 60)
                if retry is not None:
                    raise TileUpstreamError(429)
            with protect_http_logs():
                async with (
                    asyncio.timeout(DEFAULT_TIMEOUT_SECONDS),
                    self._admission,
                    self._client.stream(
                        "GET",
                        url,
                        params={"key": self._key},
                        headers={"Accept-Encoding": "identity"},
                        follow_redirects=False,
                    ) as response,
                ):
                    if response.status_code != 200:
                        raise TileUpstreamError(response.status_code)
                    content = await _bounded_tile(response)
                    content_type = response.headers.get("content-type", "image/png")
            tile = Tile(content, content_type)
            self._cache.put(cache_key, tile)
            return tile
        except TileUpstreamError:
            raise
        except (TimeoutError, httpx.HTTPError):
            raise TileUpstreamError(502) from None
        finally:
            async with self._inflight_lock:
                if self._inflight.get(cache_key) is asyncio.current_task():
                    self._inflight.pop(cache_key, None)

    async def aclose(self) -> None:
        await self._client.aclose()


async def _bounded_tile(response: httpx.Response) -> bytes:
    encoding = response.headers.get("content-encoding", "identity").casefold()
    if encoding not in ("", "identity"):
        raise TileUpstreamError(502)
    raw_length = response.headers.get("content-length")
    if raw_length is not None:
        try:
            if int(raw_length) > MAX_TILE_BYTES:
                raise TileUpstreamError(502)
        except ValueError:
            raise TileUpstreamError(502) from None
    content = bytearray()
    if response.is_stream_consumed:
        content.extend(response.content)
    else:
        async for chunk in response.aiter_raw():
            content.extend(chunk)
            if len(content) > MAX_TILE_BYTES:
                raise TileUpstreamError(502)
    if len(content) > MAX_TILE_BYTES:
        raise TileUpstreamError(502)
    if not content.startswith(b"\x89PNG"):
        raise TileUpstreamError(502)
    return bytes(content)


class NullTileProvider:
    """Stands in when no OS key is configured: nothing is fetched, nothing is cached."""

    @property
    def configured(self) -> bool:
        return False

    async def fetch(self, layer: str, z: int, x: int, y: int) -> Tile:
        raise TileUpstreamError(404)

    async def aclose(self) -> None:
        return None
