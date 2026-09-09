"""Terrarium decoding, public grid mapping and bounded shared cache behaviour."""

import asyncio
import struct
import threading
import zlib
from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from PIL import Image

from ase.adapters.routing import terrarium
from ase.adapters.routing.terrarium import TerrariumGateway, decode_terrarium, sample_terrarium
from ase.domain.events import Point
from ase.domain.terrain import terrain_pixel, terrain_resolution


def png(colour=(128, 10, 128), mode="RGB", size=(256, 256)):
    output = BytesIO()
    Image.new(mode, size, colour).save(output, format="PNG")
    return output.getvalue()


def test_rgb_fraction_negative_bathymetry_and_grid_boundaries():
    assert sample_terrarium(decode_terrarium(png()), 0, 0) == 10.5
    assert sample_terrarium(decode_terrarium(png((127, 246, 0))), 255, 255) == -10
    assert sample_terrarium(decode_terrarium(png((128, 0, 0, 255), "RGBA")), 0, 0) == 0
    assert terrain_pixel(Point(0, 0)) == ((512, 512), 0, 0)
    assert terrain_pixel(Point(180, 0)) == terrain_pixel(Point(-180, 0))
    assert terrain_pixel(Point(0, 85.05112878))[0][1] == 0
    assert terrain_pixel(Point(0, -85.05112878))[0][1] == 1023
    assert terrain_resolution((Point(0, 0), Point(0, 60))) == pytest.approx(152.8740566)
    with pytest.raises(ValueError):
        terrain_pixel(Point(0, 90))


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"not png",
        b"x" * (terrarium.TERRAIN_TILE_BYTES + 1),
        png(size=(512, 512)),
        png(10, "L"),
        png((128, 0, 0, 0), "RGBA"),
    ],
    ids=["empty", "non-png", "oversized", "dimensions", "greyscale", "transparent"],
)
def test_invalid_tile_dimensions_encoding_and_transparency(payload):
    with pytest.raises((ValueError, OSError)):
        decode_terrarium(payload)


def test_void_and_invalid_samples_never_become_zero():
    with pytest.raises(ValueError):
        sample_terrarium(decode_terrarium(png((0, 0, 0))), 0, 0)
    with pytest.raises(ValueError):
        sample_terrarium(b"", 0, 0)
    with pytest.raises(ValueError):
        sample_terrarium(decode_terrarium(png()), 256, 0)


def chunk(kind, data):
    return len(data).to_bytes(4, "big") + kind + data + zlib.crc32(kind + data).to_bytes(4, "big")


def test_compressed_metadata_is_discarded_before_image_decode():
    payload = png()
    metadata = chunk(b"zTXt", b"note\x00\x00" + zlib.compress(b"x" * 2_000_000))
    assert sample_terrarium(decode_terrarium(payload[:33] + metadata + payload[33:]), 0, 0) == 10.5


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p[:-8],
        lambda p: p[:29] + b"bad!" + p[33:],
        lambda p: p[:33] + p[8:33] + p[33:],
        lambda p: p[:8] + chunk(b"tEXt", b"note\x00data") + p[8:],
        lambda p: p[:33] + chunk(b"tRNS", b"\x00" * 6) + p[33:],
        lambda p: p[:33] + chunk(b"ABCD", b"data") + p[33:],
        lambda p: p[:-12] + chunk(b"IEND", b"data"),
        lambda p: p[:8],
        lambda p: p[:8] + chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 2, 2, 0, 0)) + p[33:],
    ],
    ids=[
        "truncated",
        "checksum",
        "duplicate-header",
        "header-order",
        "transparent-colour",
        "critical-chunk",
        "nonempty-end",
        "no-chunks",
        "compression",
    ],
)
def test_unsafe_png_chunks_fail_closed(mutation):
    with pytest.raises(ValueError):
        decode_terrarium(mutation(png()))


async def test_same_tile_coalesces_caches_and_lru_is_bounded(monkeypatch):
    monkeypatch.setattr(terrarium, "CACHE_TILES", 2)
    entered, release = asyncio.Event(), asyncio.Event()

    async def fetch(*args):
        entered.set()
        await release.wait()
        return png()

    http = Mock(get_secret_bytes=AsyncMock(side_effect=fetch))
    gateway = TerrariumGateway(http)
    first = asyncio.create_task(gateway.elevations((Point(0, 0),)))
    await entered.wait()
    second = asyncio.create_task(gateway.elevations((Point(0, 0), Point(0.001, 0))))
    await asyncio.sleep(0)
    release.set()
    assert await first == (10.5,)
    assert await second == (10.5, 10.5)
    assert http.get_secret_bytes.await_count == 1
    target = http.get_secret_bytes.call_args.args[0]
    assert target.url == "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/10/512/512.png"
    assert "/512/512" not in repr(target)
    assert await gateway.elevations((Point(0, 0),)) == (10.5,)
    assert http.get_secret_bytes.await_count == 1
    await gateway.elevations((Point(1, 0), Point(2, 0)))
    assert len(gateway._cache) == 2
    await gateway.elevations((Point(0, 0),))
    assert http.get_secret_bytes.await_count == 4
    await gateway.aclose()
    assert not gateway._cache and not gateway._pending


async def test_cancelling_one_waiter_preserves_shared_fetch_and_last_waiter_cancels():
    entered, release, cancelled = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def fetch(*args):
        entered.set()
        try:
            await release.wait()
            return png()
        finally:
            cancelled.set()

    http = Mock(get_secret_bytes=AsyncMock(side_effect=fetch))
    gateway = TerrariumGateway(http)
    first = asyncio.create_task(gateway.elevations((Point(0, 0),)))
    await entered.wait()
    second = asyncio.create_task(gateway.elevations((Point(0, 0),)))
    for _ in range(5):
        await asyncio.sleep(0)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert not cancelled.is_set()
    release.set()
    assert await second == (10.5,)
    release.clear()
    entered.clear()
    cancelled.clear()
    final = asyncio.create_task(gateway.elevations((Point(2, 0),)))
    await entered.wait()
    final.cancel()
    with pytest.raises(asyncio.CancelledError):
        await final
    assert cancelled.is_set() and not gateway._pending


async def test_at_most_four_tile_downloads_and_failure_releases_work():
    active = peak = 0
    release, entered = asyncio.Event(), asyncio.Event()

    async def fetch(*args):
        nonlocal active, peak
        active += 1
        peak = max(active, peak)
        if active == 4:
            entered.set()
        try:
            await release.wait()
            return png()
        finally:
            active -= 1

    http = Mock(get_secret_bytes=AsyncMock(side_effect=fetch))
    gateway = TerrariumGateway(http)
    task = asyncio.create_task(gateway.elevations(tuple(Point(i, 0) for i in range(8))))
    await entered.wait()
    assert peak == 4
    release.set()
    assert len(await task) == 8 and peak == 4
    http.get_secret_bytes.side_effect = RuntimeError("upstream location")
    with pytest.raises(ExceptionGroup):
        await gateway.elevations((Point(20, 0), Point(21, 0)))
    assert not gateway._pending
    await gateway.aclose()


async def test_decode_cancellation_keeps_worker_bounded_until_it_finishes(monkeypatch):
    started, finish = threading.Event(), threading.Event()
    decode = decode_terrarium

    def blocked(payload):
        started.set()
        finish.wait(timeout=2)
        return decode(payload)

    monkeypatch.setattr(terrarium, "decode_terrarium", blocked)
    gateway = TerrariumGateway(Mock(get_secret_bytes=AsyncMock(return_value=png())))
    task = asyncio.create_task(gateway.elevations((Point(0, 0),)))
    await asyncio.wait_for(asyncio.to_thread(started.wait), timeout=1)
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not gateway._cache and not gateway._pending
    await gateway.aclose()
