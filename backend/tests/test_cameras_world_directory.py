"""Bounded regional directory lookups and no arbitrary camera playback."""

import json
from unittest.mock import AsyncMock

import pytest

from ase.adapters.geo.camera_world_directory import (
    BATCH,
    MARKERS,
    REGIONS,
    build_sources,
    map_record,
    regional_ids,
)


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
