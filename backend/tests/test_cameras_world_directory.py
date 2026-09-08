"""Bounded regional directory lookups and no arbitrary camera playback."""

import asyncio
import json
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.geo.camera_registry import GuardedCameraSource
from ase.adapters.geo.camera_world_directory import (
    BATCH,
    MARKERS,
    REGIONS,
    build_sources,
    map_record,
    regional_ids,
)
from ase.application.cameras import CameraCatalogueService


def test_spatial_sampling_is_even_bounded_and_ignores_invalid_rows():
    index = {"ids": [str(i) for i in range(2400)], "lats": [35] * 2400, "lngs": [139] * 2400}
    ids = regional_ids(index, "eastasia")
    assert len(ids) == 1200 and ids[:3] == ["0", "2", "4"] and ids[-1] == "2398"
    assert regional_ids(
        {
            "ids": ["a", "b", None, "c", "d"],
            "lats": [35, "bad", 35, float("nan"), 70],
            "lngs": [139, 139, 139, 139, 139],
        },
        "eastasia",
    ) == ["a"]
    for invalid in [None, {}, {"ids": [], "lats": [], "lngs": None}]:
        with pytest.raises(ValueError, match="marker index"):
            regional_ids(invalid, "eastasia")


def test_unknown_camera_hosts_remain_directory_links():
    row = {
        "id": "1",
        "lat": 35,
        "lng": 139,
        "name": "Directory camera",
        "feed_type": "hls",
        "feed_url": "http://192.168.0.1/private.m3u8",
    }
    camera = map_record("eastasia", row)
    assert camera is not None and camera.snapshot_url is None and camera.stream_url is None
    assert camera.external_url == "https://opencctv.org/"
    assert camera.coordinate_precision == "approximate"
    assert map_record("eastasia", {**row, "active": 0}) is None
    assert map_record("eastasia", {**row, "lat": 300}) is None
    assert map_record("eastasia", None) is None


async def test_fixed_read_only_batches_ignore_unrequested_rows():
    http = AsyncMock()
    http.get_bytes.return_value = json.dumps({"ids": ["1"], "lats": [35], "lngs": [139]}).encode()
    http.post_json.return_value = [
        {"id": "1", "lat": 35, "lng": 139},
        {"id": "2", "lat": 35, "lng": 139},
        {"id": ["1"], "lat": 35, "lng": 139},
        {"id": {"key": "1"}, "lat": 35, "lng": 139},
    ]
    sources = build_sources(http)
    assert {source.id for source in sources} == set(REGIONS)
    cameras = await sources[0].fetch()
    assert len(cameras) == 1 and cameras[0].id == "opencctv:1"
    http.get_bytes.assert_awaited_once_with(MARKERS, conditional=False, max_redirects=0)
    http.post_json.assert_awaited_once_with(BATCH, {"ids": ["1"]})


async def test_bad_batch_fails_source_instead_of_empty_success():
    http = AsyncMock()
    http.get_bytes.return_value = b'{"ids":["1"],"lats":[35],"lngs":[139]}'
    http.post_json.return_value = {"error": "temporarily unavailable"}
    with pytest.raises(ValueError, match="batch"):
        await build_sources(http)[0].fetch()


async def test_regions_share_one_index_download():
    http = AsyncMock()
    http.get_bytes.return_value = b'{"ids":["1"],"lats":[35],"lngs":[139]}'
    http.post_json.return_value = [{"id": "1", "lat": 35, "lng": 139}]
    sources = build_sources(http)
    await asyncio.gather(*(source.fetch() for source in sources))
    assert http.get_bytes.await_count == 1


async def test_partial_batches_keep_successes_with_explicit_warning():
    http = AsyncMock()
    http.get_bytes.return_value = json.dumps(
        {
            "ids": [str(i) for i in range(51)],
            "lats": [35] * 51,
            "lngs": [139] * 51,
        }
    ).encode()

    async def post(_url, payload):
        if payload["ids"] == ["50"]:
            raise ValueError("upstream failure")
        return [{"id": key, "lat": 35, "lng": 139} for key in payload["ids"]]

    http.post_json.side_effect = post
    source = build_sources(http)[0]
    cameras = await source.fetch()
    assert len(cameras) == 50
    assert source.warning == "Partial directory catalogue: 1/2 batches loaded."
    http.post_json.side_effect = lambda _url, payload: [
        {"id": key, "lat": 35, "lng": 139} for key in payload["ids"]
    ]
    assert len(await source.fetch()) == 51
    assert source.warning is None


async def test_caller_cancellation_is_not_a_partial_success():
    http = AsyncMock()
    http.get_bytes.return_value = b'{"ids":["1"],"lats":[35],"lngs":[139]}'
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def post(*args):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    http.post_json.side_effect = post
    task = asyncio.create_task(build_sources(http)[0].fetch())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()


async def test_slow_batch_deadline_preserves_other_batches(monkeypatch):
    monkeypatch.setattr("ase.adapters.geo.camera_world_directory.BATCH_BUDGET_SECONDS", 0.02)
    http = AsyncMock()
    http.get_bytes.return_value = json.dumps(
        {
            "ids": [str(i) for i in range(51)],
            "lats": [35] * 51,
            "lngs": [139] * 51,
        }
    ).encode()

    async def post(_url, payload):
        if payload["ids"] == ["50"]:
            await asyncio.Event().wait()
        return [{"id": key, "lat": 35, "lng": 139} for key in payload["ids"]]

    http.post_json.side_effect = post
    source = build_sources(http)[0]
    assert len(await source.fetch()) == 50
    assert source.warning == "Partial directory catalogue: 1/2 batches loaded."


async def test_partial_warning_survives_guard_and_retries_after_one_minute(user, clock):
    upstream = AsyncMock()
    upstream.id, upstream.name = "eastasia", "East Asia"
    upstream.warning = "Partial directory catalogue: 1/2 batches loaded."
    upstream.fetch.return_value = (map_record("eastasia", {"id": "1", "lat": 35, "lng": 139}),)
    service = CameraCatalogueService((GuardedCameraSource(upstream),), clock)
    result = await service.catalogue(user)
    assert result.providers[0].message == upstream.warning
    assert len(result.cameras) == 1
    clock.advance(timedelta(seconds=59))
    await service.catalogue(user)
    assert upstream.fetch.await_count == 1
    clock.advance(timedelta(seconds=2))
    upstream.warning = None
    result = await service.catalogue(user)
    assert upstream.fetch.await_count == 2
    assert result.providers[0].message is None
