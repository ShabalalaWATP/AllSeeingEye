"""The OS Maps tile proxy: key handling, caching, validation and the capabilities flag."""

from __future__ import annotations

import asyncio
import logging

import httpx
import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from ase.adapters.tiles.os_maps import (
    MAX_TILE_BYTES,
    NullTileProvider,
    OsMapsTileProvider,
    TileCache,
)
from ase.application.ports.tiles import Tile, TileUpstreamError, is_valid_os_tile
from ase.container import Container
from ase.domain.users import User
from ase.infrastructure.settings import Environment, Settings
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

PNG = b"\x89PNG-not-really"


class FakeTiles:
    def __init__(self, failures: dict[tuple[int, int, int], int] | None = None) -> None:
        self.failures = failures or {}
        self.calls: list[tuple[str, int, int, int]] = []

    @property
    def configured(self) -> bool:
        return True

    async def fetch(self, layer: str, z: int, x: int, y: int) -> Tile:
        self.calls.append((layer, z, x, y))
        status = self.failures.get((z, x, y))
        if status is not None:
            raise TileUpstreamError(status)
        return Tile(PNG, "image/png")

    async def aclose(self) -> None:
        return None


def test_cache_is_bounded_by_bytes() -> None:
    cache = TileCache(max_bytes=10)
    cache.put("a", Tile(b"123456", "image/png"))
    cache.put("b", Tile(b"abcdef", "image/png"))
    assert cache.get("a") is None and cache.get("b") is not None
    assert len(cache) == 1 and cache.bytes == 6
    cache.put("c", Tile(b"12", "image/png"))
    assert cache.get("b") is not None  # touched, so it stays newest
    cache.put("d", Tile(b"1234", "image/png"))
    assert cache.get("c") is None and cache.get("b") is not None
    cache.put("b", Tile(b"12345", "image/png"))  # replacing keeps the byte count right
    assert cache.bytes == 9
    cache.put("huge", Tile(b"x" * 11, "image/png"))
    assert cache.get("huge") is None


async def test_provider_sends_the_key_and_caches() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/7/62/40.png"):
            return httpx.Response(200, content=PNG, headers={"content-type": "image/png"})
        if request.url.path.endswith("/7/0/0.png"):
            raise httpx.ConnectError("boom")
        return httpx.Response(429)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OsMapsTileProvider("secret-key", client=client)
    assert provider.configured
    tile = await provider.fetch("Road_3857", 7, 62, 40)
    assert tile.content == PNG and tile.content_type == "image/png"
    assert (await provider.fetch("Road_3857", 7, 62, 40)) is tile
    assert len(requests) == 1
    assert requests[0].url.params["key"] == "secret-key"
    assert requests[0].url.host == "api.os.uk"
    with pytest.raises(TileUpstreamError) as limited:
        await provider.fetch("Road_3857", 7, 1, 1)
    assert limited.value.status == 429
    with pytest.raises(TileUpstreamError) as down:
        await provider.fetch("Road_3857", 7, 0, 0)
    assert down.value.status == 502
    await provider.aclose()

    null = NullTileProvider()
    assert not null.configured
    with pytest.raises(TileUpstreamError):
        await null.fetch("Road_3857", 7, 62, 40)
    await null.aclose()


@pytest.mark.parametrize(
    ("headers", "content"),
    [
        ({"content-length": str(MAX_TILE_BYTES + 1)}, PNG),
        ({"content-encoding": "gzip"}, PNG),
        ({}, PNG + b"x" * MAX_TILE_BYTES),
        ({}, b"not-a-png"),
    ],
    ids=("declared-oversize", "encoded", "actual-oversize", "invalid-image"),
)
async def test_provider_rejects_unsafe_tile_bodies(headers: dict[str, str], content: bytes) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, headers=headers, content=content)
        )
    )
    provider = OsMapsTileProvider("secret-key", client=client)
    with pytest.raises(TileUpstreamError) as failure:
        await provider.fetch("Road_3857", 7, 62, 40)
    assert failure.value.status == 502
    await provider.aclose()


async def test_provider_global_quota_refuses_before_sending_key() -> None:
    requests: list[httpx.Request] = []
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: (requests.append(request), httpx.Response(200, content=PNG))[1]
        )
    )

    class Limited:
        def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
            assert (key, limit, window_seconds) == ("os-maps:global", 540, 60)
            return 1

    limiter = Limited()
    provider = OsMapsTileProvider("secret-key", client=client, limiter=limiter)
    with pytest.raises(TileUpstreamError) as limited:
        await provider.fetch("Road_3857", 7, 62, 40)
    assert limited.value.status == 429 and requests == []
    await provider.aclose()


async def test_same_tile_is_coalesced_and_secret_url_logs_are_suppressed(caplog) -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        started.set()
        await release.wait()
        return httpx.Response(200, content=PNG)

    caplog.set_level(logging.DEBUG, logger="httpx")
    caplog.set_level(logging.DEBUG, logger="httpcore")
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OsMapsTileProvider("secret-key", client=client)
    first = asyncio.create_task(provider.fetch("Road_3857", 7, 62, 40))
    await started.wait()
    second = asyncio.create_task(provider.fetch("Road_3857", 7, 62, 40))
    await asyncio.sleep(0)
    release.set()
    assert [tile.content for tile in await asyncio.gather(first, second)] == [PNG, PNG]
    assert len(requests) == 1
    assert "secret-key" not in caplog.text
    logging.getLogger("httpx").info("ordinary-http-log-resumed")
    assert "ordinary-http-log-resumed" in caplog.text
    await provider.aclose()


def test_validation_and_settings() -> None:
    assert is_valid_os_tile("Road_3857", 7, 62, 40)
    assert is_valid_os_tile("Light_3857", 16, 65535, 65535)
    assert not is_valid_os_tile("Leisure_27700", 7, 62, 40)
    assert not is_valid_os_tile("Road_3857", 6, 1, 1)
    assert not is_valid_os_tile("Road_3857", 17, 1, 1)
    assert not is_valid_os_tile("Road_3857", 7, 128, 1)
    assert not is_valid_os_tile("Road_3857", 7, -1, 1)
    blank = Settings(_env_file=None, env=Environment.TEST, os_maps_key=SecretStr("  "))
    assert blank.os_maps_key_value is None
    keyed = Settings(_env_file=None, env=Environment.TEST, os_maps_key=SecretStr(" abc "))
    assert keyed.os_maps_key_value == "abc"


async def test_endpoints_without_a_key(client: AsyncClient, user: User) -> None:
    assert (await client.get("/api/capabilities")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    caps = await client.get("/api/capabilities", headers=bearer(token))
    assert caps.status_code == 200 and caps.json() == {"os_maps": False, "os_layers": []}
    tile = await client.get("/api/tiles/os/Road_3857/7/62/40.png", headers=bearer(token))
    assert tile.status_code == 404
    assert tile.json()["error"]["code"] == "not_found"
    assert (await client.get("/api/tiles/os/Road_3857/7/62/40.png")).status_code == 401


async def test_endpoints_with_a_key(client: AsyncClient, container: Container, user: User) -> None:
    fake = FakeTiles(failures={(7, 1, 1): 404, (7, 2, 2): 500})
    container.tiles = fake
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    caps = await client.get("/api/capabilities", headers=bearer(token))
    assert caps.json() == {
        "os_maps": True,
        "os_layers": ["Light_3857", "Outdoor_3857", "Road_3857"],
    }
    tile = await client.get("/api/tiles/os/Road_3857/7/62/40.png", headers=bearer(token))
    assert tile.status_code == 200
    assert tile.content == PNG
    assert tile.headers["content-type"] == "image/png"
    assert tile.headers["cache-control"] == "private, max-age=86400"
    assert fake.calls == [("Road_3857", 7, 62, 40)]
    bad = await client.get("/api/tiles/os/Leisure_27700/7/62/40.png", headers=bearer(token))
    assert bad.status_code == 422
    assert bad.json()["error"]["fields"] == {"tile": "Unknown OS layer or tile address."}
    assert (
        await client.get("/api/tiles/os/Road_3857/17/1/1.png", headers=bearer(token))
    ).status_code == 422
    assert (
        await client.get("/api/tiles/os/Road_3857/7/-1/1.png", headers=bearer(token))
    ).status_code == 422
    missing = await client.get("/api/tiles/os/Road_3857/7/1/1.png", headers=bearer(token))
    assert missing.status_code == 404
    broken = await client.get("/api/tiles/os/Road_3857/7/2/2.png", headers=bearer(token))
    assert broken.status_code == 502
    assert broken.json()["error"]["code"] == "upstream_unavailable"
