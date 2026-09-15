"""Traffic Scotland index, same-origin frame relay and curated UK catalogue regressions."""

import asyncio
import base64
import json
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.http import FeedHttpStatusError
from ase.adapters.geo.camera_britain import (
    CURATED,
    FRAME,
    INDEX,
    INDEX_RETRY_SECONDS,
    TrafficScotlandSource,
    build_sources,
    curated,
    extract_frame,
    parse_scotland,
)
from ase.adapters.geo.camera_registry import GuardedCameraSource

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
ROW = {
    "sid": "1",
    "title": "M8 Kingston Br",
    "lat": "55.852826000000",
    "lng": "-4.270806100000",
    "roadname": "M8",
    "images": "16",
    "region": "Strathclyde",
}


def snippet(data: bytes = JPEG) -> bytes:
    encoded = base64.b64encode(data)
    return (
        b'<div class="camera-image" tid="16"><img src="data:image/jpeg;base64,'
        + encoded
        + b'" /></div>'
    )


def index(rows: list[object]) -> bytes:
    return json.dumps({"status": "ok", "results": rows}).encode()


def test_index_rows_become_relay_cameras_within_scotland() -> None:
    cameras = parse_scotland(
        index(
            [
                ROW,
                {**ROW, "sid": "2", "lat": "51.5", "lng": "-0.1"},
                {**ROW, "sid": "abc"},
                {**ROW, "sid": "3", "lat": "north"},
                "junk",
                {**ROW, "region": ""},
            ]
        )
    )
    assert [camera.id for camera in cameras] == ["traffic-scotland:1"]
    camera = cameras[0]
    assert camera.snapshot_url == "/api/cameras/frames/traffic-scotland/1.jpg"
    assert camera.title == "M8 Kingston Br"
    assert camera.coordinate_precision == "exact"
    assert (
        camera.external_url == camera.source_url == "https://www.traffic.gov.scot/traffic-cameras"
    )
    assert parse_scotland(index([ROW]))[0].title == "M8 Kingston Br (Strathclyde)"
    for payload in [b"[]", b"{}", b'{"results": {}}', b'{"results": []}', b'{"results": [1]}']:
        with pytest.raises(ValueError, match="Traffic Scotland"):
            parse_scotland(payload)


def test_extract_frame_requires_a_bounded_inline_jpeg() -> None:
    assert extract_frame(snippet()) == JPEG
    assert extract_frame(b"<div>no image</div>") is None
    assert extract_frame(snippet(b"GIF89a" + b"\x00" * 64)) is None
    assert extract_frame(b"data:image/jpeg;base64," + b"A" * 65) is None
    assert extract_frame(snippet(b"\xff\xd8\xff" + b"\x00" * (2 * 1024 * 1024))) is None


async def test_frames_only_for_indexed_sids_with_cache_and_fixed_urls() -> None:
    http = AsyncMock()
    second = b"\xff\xd8\xff" + b"\x01" * 64
    http.get_bytes.side_effect = [index([ROW]), snippet(), snippet(second)]
    clock = [0.0]
    source = TrafficScotlandSource(http, clock=lambda: clock[0])
    assert await source.frame("../1") is None
    assert await source.frame("1") == JPEG
    assert http.get_bytes.await_args_list[0].args == (INDEX,)
    assert http.get_bytes.await_args_list[1].args == (FRAME + "1",)
    assert http.get_bytes.await_args_list[1].kwargs == {"conditional": False, "max_redirects": 0}
    assert await source.frame("1") == JPEG
    assert http.get_bytes.await_count == 2
    clock[0] = 60.0
    assert await source.frame("1") == second
    assert http.get_bytes.await_count == 3
    assert await source.frame("2") is None
    assert http.get_bytes.await_count == 3


async def test_failed_index_load_cools_down_and_is_shared_by_frame_requests() -> None:
    http = AsyncMock()
    http.get_bytes.side_effect = FeedHttpStatusError(503, INDEX)
    clock = [0.0]
    source = TrafficScotlandSource(http, clock=lambda: clock[0])
    for _ in range(10):
        with pytest.raises((FeedHttpStatusError, ValueError)):
            await source.frame("1")
    assert http.get_bytes.await_count == 1
    with pytest.raises(ValueError, match="frame unavailable"):
        await GuardedCameraSource(source).frame("1")
    assert http.get_bytes.await_count == 1

    clock[0] = INDEX_RETRY_SECONDS + 1

    async def slow_failure(*_: object, **__: object) -> bytes:
        await asyncio.sleep(0.01)
        raise FeedHttpStatusError(503, INDEX)

    http.get_bytes.side_effect = slow_failure
    results = await asyncio.gather(*(source.frame("1") for _ in range(10)), return_exceptions=True)
    assert all(isinstance(result, Exception) for result in results)
    assert http.get_bytes.await_count == 2

    clock[0] = 2 * INDEX_RETRY_SECONDS + 2
    http.get_bytes.side_effect = [index([ROW]), snippet()]
    assert await source.frame("1") == JPEG
    assert http.get_bytes.await_count == 4


async def test_frame_without_an_image_is_a_provider_failure_even_when_guarded() -> None:
    http = AsyncMock()
    http.get_bytes.side_effect = [index([ROW]), b"<div>error</div>"]
    source = TrafficScotlandSource(http)
    assert len(await source.fetch()) == 1
    with pytest.raises(ValueError, match="no image"):
        await source.frame("1")
    http.get_bytes.side_effect = [b"<div>error</div>"]
    with pytest.raises(ValueError, match="frame unavailable"):
        await GuardedCameraSource(source).frame("1")
    assert await GuardedCameraSource(AsyncMock(spec=["id", "name", "fetch"])).frame("1") is None


def test_curated_catalogues_keep_hosts_and_provenance() -> None:
    for provider in CURATED:
        cameras = curated(provider)
        assert cameras
        assert len({camera.id for camera in cameras}) == len(cameras)
        if provider == "durham":
            assert all(camera.coordinate_precision == "exact" for camera in cameras)
            assert all(
                str(camera.snapshot_url).startswith("https://dcc.ussgroup.co.uk/images/dutmc_")
                for camera in cameras
            )
            assert all(
                str(camera.external_url).startswith("https://www.durham.gov.uk/")
                for camera in cameras
            )
        elif provider == "uk-live":
            assert all(camera.coordinate_precision == "approximate" for camera in cameras)
            assert all(camera.stream_type == "iframe" for camera in cameras)
            assert all(
                str(camera.stream_url).startswith("https://www.youtube.com/embed/")
                for camera in cameras
            )
            assert all("not verified" in camera.attribution for camera in cameras)
        else:
            assert all(camera.coordinate_precision == "approximate" for camera in cameras)
            assert all(camera.snapshot_url or camera.stream_type == "hls" for camera in cameras)
            assert all("not verified" in camera.attribution for camera in cameras)
    local = {camera.id: camera for camera in curated("uk-local")}
    assert local["uk-local:mersey-gateway-runcorn"].stream_url == (
        "https://stream1.mgw-is.uk/hls/stream.m3u8"
    )
    assert str(local["uk-local:iom-peel"].snapshot_url).startswith("https://images.gov.im/")
    assert len(local) >= 40
    scotland = [camera for camera in curated("uk-live") if "Scotland" in camera.attribution]
    assert not scotland  # attribution names the owner, never a guessed nation
    assert len([camera for camera in curated("uk-live") if camera.latitude > 55]) >= 10


@pytest.mark.parametrize(
    "row",
    [
        {"stream_type": "iframe", "stream_url": "https://www.youtube.com/embed/short"},
        {"stream_type": "iframe", "stream_url": "https://www.youtube.com/watch?v=abcdefghijk"},
        {"stream_type": "hls", "stream_url": "https://www.youtube.com/embed/abcdefghijk"},
        {"feed_url": "https://dcc.ussgroup.co.uk.evil.test/images/dutmc_1.jpg"},
        {"feed_url": "http://dcc.ussgroup.co.uk/images/dutmc_1.jpg"},
        {"external_url": "https://evil.test/"},
        {"feed_url": "https://user@dcc.ussgroup.co.uk/images/dutmc_1.jpg"},
    ],
)
def test_curated_rows_cannot_widen_media_origins(row: dict[str, object]) -> None:
    record = {"provider": "uk-live", "id": "x", "lat": 51.5, "lng": -1.0, **row}
    assert curated("uk-live", [record]) == ()


async def test_build_sources_are_distinct_and_fetch_the_fixed_index() -> None:
    http = AsyncMock()
    http.get_bytes.return_value = index([ROW])
    sources = build_sources(http)
    ids = [source.id for source in sources]
    assert ids == ["traffic-scotland", "durham", "uk-live", "uk-local"]
    assert len(await sources[0].fetch()) == 1
    http.get_bytes.assert_awaited_once_with(INDEX, conditional=False, max_redirects=0)
    for source in sources[1:]:
        assert await source.fetch()
