"""Ordnance Survey raster tiles fetched with the server-side key and cached in memory.

The OS Data Hub free plan allows 600 transactions a minute per API; a bounded
least-recently-used cache keeps repeated views of the same area from spending them.
"""

from __future__ import annotations

from collections import OrderedDict

import httpx

from ase.application.ports.tiles import Tile, TileUpstreamError

UPSTREAM = "https://api.os.uk/maps/raster/v1/zxy/{layer}/{z}/{x}/{y}.png"
DEFAULT_CACHE_BYTES = 64 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 15.0


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
    ) -> None:
        self._key = key
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(DEFAULT_TIMEOUT_SECONDS))
        self._cache = cache or TileCache()

    @property
    def configured(self) -> bool:
        return True

    async def fetch(self, layer: str, z: int, x: int, y: int) -> Tile:
        cache_key = f"{layer}/{z}/{x}/{y}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        url = UPSTREAM.format(layer=layer, z=z, x=x, y=y)
        try:
            response = await self._client.get(url, params={"key": self._key})
        except httpx.HTTPError as exc:
            raise TileUpstreamError(502) from exc
        if response.status_code != 200:
            raise TileUpstreamError(response.status_code)
        tile = Tile(response.content, response.headers.get("content-type", "image/png"))
        self._cache.put(cache_key, tile)
        return tile

    async def aclose(self) -> None:
        await self._client.aclose()


class NullTileProvider:
    """Stands in when no OS key is configured: nothing is fetched, nothing is cached."""

    @property
    def configured(self) -> bool:
        return False

    async def fetch(self, layer: str, z: int, x: int, y: int) -> Tile:
        raise TileUpstreamError(404)

    async def aclose(self) -> None:
        return None
