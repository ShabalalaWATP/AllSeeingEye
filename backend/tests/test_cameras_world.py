"""World camera parsers, public media allowlists and catalogue semantics."""

import json
from unittest.mock import AsyncMock

import pytest

from ase.adapters.geo.camera_world import (
    ENDPOINTS,
    NAMES,
    build_sources,
    make_camera,
    media_url,
    parse_australia,
    parse_newzealand,
    parse_singapore,
    parse_taiwan,
)


@pytest.mark.parametrize(
    "url",
    [
        None,
        1,
        "http://trafficnz.info/camera/1.jpg",
        "https://trafficnz.info:443/x",
        "https://trafficnz.info.evil.test/x",
        "https://user@trafficnz.info/x",
        "https://127.0.0.1/x",
        "https://trafficnz.info/x#frag",
        "https://trafficnz.info/\nx",
        "https://[invalid/x",
        "https://trafficnz.info/" + "x" * 2048,
    ],
)
def test_refuses_unapproved_media(url):
    assert media_url(url) is None


def test_catalogue_validation_and_stream_capability():
    row = {
        "id": "camera-1",
        "lat": 35,
        "lng": 139,
        "name": "Public webcam",
        "stream_url": "https://www.youtube.com/embed/UemFRPrl1hk",
        "approximate": True,
    }
    camera = make_camera("japan", row)
    assert camera is not None and camera.snapshot_url is None
    assert camera.stream_type == "iframe" and camera.coordinate_precision == "approximate"
    for mutation in [
        {"id": ""},
        {"id": "x" * 161},
        {"lat": "bad"},
        {"lat": None},
        {"lat": float("nan")},
        {"lng": 181},
        {"stream_url": "https://www.youtube.com/watch?v=UemFRPrl1hk"},
    ]:
        assert make_camera("japan", {**row, **mutation}) is None


def test_nsw_only_camera_features_and_approved_images():
    row = {
        "eventType": "liveCams",
        "path": "one",
        "geometry": {"coordinates": [151, -34]},
        "properties": {
            "title": "Road camera",
            "href": "https://webcams.transport.nsw.gov.au/cameras/one.jpeg",
        },
    }
    data = [
        row,
        row,
        {},
        None,
        {**row, "geometry": {"coordinates": []}},
        {**row, "properties": {"href": "https://evil.test/cam.jpg"}},
    ]
    cameras = parse_australia(json.dumps(data).encode())
    assert len(cameras) == 1 and cameras[0].latitude == -34
    with pytest.raises(ValueError, match="NSW"):
        parse_australia(b"{}")


def test_nzta_nested_ids_offline_and_geometry():
    body = """<camera><id>1</id><name>Main road</name><region><id>22</id></region>
    <latitude>-40</latitude><longitude>174</longitude><imageUrl>/camera/1.jpg</imageUrl>
    </camera>"""
    payload = "<cameras>" + body + body.replace("</camera>", "<offline>true</offline></camera>")
    payload += body.replace("</camera>", "<underMaintenance>true</underMaintenance></camera>")
    payload += body.replace("-40", "30") + body.replace("/camera/1.jpg", "") + "</cameras>"
    cameras = parse_newzealand(payload.encode())
    assert len(cameras) == 1 and cameras[0].id == "newzealand:1"
    assert cameras[0].snapshot_url == "https://trafficnz.info/camera/1.jpg"


def test_taiwan_snapshots_reject_outside_region_or_unapproved_hosts():
    row = {
        "id": "one",
        "stakenumber": "Highway 1",
        "gisy": "25",
        "gisx": "121",
        "html": "https://cctv-ss01.thb.gov.tw/camera/1",
    }
    rows = [row, None, {**row, "gisy": "0"}, {**row, "html": "http://127.0.0.1/x"}]
    cameras = parse_taiwan(json.dumps(rows).encode())
    assert len(cameras) == 1 and cameras[0].snapshot_url.endswith("/snapshot")
    with pytest.raises(ValueError, match="Taiwan"):
        parse_taiwan(b"{}")


def test_singapore_and_bad_catalogues():
    row = {
        "camera_id": "1",
        "location": {"latitude": 1.3, "longitude": 103.8},
        "image": "https://images.data.gov.sg/api/traffic-images/one.jpg",
    }
    cameras = parse_singapore(json.dumps({"items": [{"cameras": [row, None]}]}).encode())
    assert len(cameras) == 1 and cameras[0].title == "LTA camera 1"
    for payload in [b"[]", b"{}", b'{"items": []}', b'{"items": [1]}']:
        with pytest.raises(ValueError, match="Singapore"):
            parse_singapore(payload)


async def test_all_curated_sources_preserve_external_only_skyline():
    http = AsyncMock()
    sources = build_sources(http)
    assert {source.id for source in sources} == set(NAMES)
    count = 0
    for source in sources:
        if source.id in ENDPOINTS:
            continue
        cameras = await source.fetch()
        assert cameras and all(camera.coordinate_precision == "approximate" for camera in cameras)
        count += len(cameras)
        if source.id in {"asia-live", "latam-live", "europe-live", "africa-live"}:
            assert all(
                camera.snapshot_url is None and camera.stream_url is None for camera in cameras
            )
            assert all(
                camera.external_url.startswith("https://www.skylinewebcams.com/")
                for camera in cameras
            )
    assert count == 666
    http.get_bytes.assert_not_called()


async def test_dynamic_sources_use_fixed_endpoints_no_redirects():
    http = AsyncMock()
    http.get_bytes.return_value = b"[]"
    source = next(source for source in build_sources(http) if source.id == "australia")
    assert await source.fetch() == ()
    http.get_bytes.assert_awaited_once_with(
        ENDPOINTS["australia"], conditional=False, max_redirects=0
    )
