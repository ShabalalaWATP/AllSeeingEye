"""Offline official camera shapes, paging and media trust-boundary regressions."""

import json
from unittest.mock import AsyncMock

import pytest

from ase.adapters.geo.camera_americas import (
    AmericanCameraSource,
    AmericanPublishedLinks,
    build_sources,
)
from ase.adapters.geo.camera_americas_common import camera, media_url
from ase.adapters.geo.camera_americas_ibi import CONFIGS, IbiCameraSource, parse_record
from ase.adapters.geo.camera_americas_parsers import parse_index, parse_row


def ibi_row(key=1):
    return {
        "id": key,
        "location": "I-15 at Main Street",
        "latLng": {"geography": {"wellKnownText": "POINT (-115.1 36.2)"}},
        "images": [
            {
                "imageUrl": f"/map/Cctv/{key}",
                "videoUrl": "https://d1wse1.its.nv.gov/camera/playlist.m3u8",
            }
        ],
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://511on.ca/a",
        "https://511on.ca.evil.test/a",
        "https://user:pass@511on.ca/a",
        "https://511on.ca:444/a",
        "https://[bad/a",
        "https://127.0.0.1/a",
        "https://511on.ca/a\nb",
        None,
        "x" * 2049,
    ],
)
def test_media_rejects_untrusted_origins(url):
    assert media_url(url) is None


@pytest.mark.parametrize("lat,lon", [("NaN", 1), (1, "inf"), (91, 1), (1, 181), (None, 1)])
def test_coordinates_rejected(lat, lon):
    assert (
        camera(
            "ontario",
            "Ontario",
            "https://511on.ca",
            1,
            "A",
            lat,
            lon,
            "https://511on.ca/map/Cctv/1",
        )
        is None
    )


def test_provider_media_not_cross_assigned():
    assert (
        camera(
            "ontario",
            "Ontario",
            "https://511on.ca",
            1,
            "A",
            43,
            -79,
            "https://tripcheck.com/camera.jpg",
        )
        is None
    )


def test_ibi_media_flags_and_coordinates():
    cfg = CONFIGS[1]
    row = ibi_row()
    cam = parse_record(cfg, row)
    assert cam and cam.stream_type == "hls" and cam.snapshot_url.endswith("/1")
    row["images"][0]["isVideoAuthRequired"] = True
    assert parse_record(cfg, row).stream_url is None
    row["images"][0]["disabled"] = True
    assert parse_record(cfg, row) is None
    row = ibi_row()
    row["latLng"]["geography"]["wellKnownText"] = "POINT (0 0)"
    assert parse_record(cfg, row) is None


@pytest.mark.parametrize(
    "row",
    [
        None,
        {},
        {"id": True},
        {"id": 1, "images": []},
        {"id": 1, "images": [3]},
        {"id": 1, "images": [{}], "latLng": "bad"},
        {"id": 1, "images": [{}], "latLng": {"geography": "bad"}},
    ],
)
def test_ibi_malformed_rows(row):
    assert parse_record(CONFIGS[1], row) is None


async def test_paging_complete_and_failure_visible():
    http = AsyncMock()
    http.get_bytes.side_effect = [
        json.dumps({"recordsTotal": 101, "data": [ibi_row(i) for i in range(100)]}).encode(),
        json.dumps({"recordsTotal": 101, "data": [ibi_row(100)]}).encode(),
    ]
    result = await IbiCameraSource(CONFIGS[1], http).fetch()
    assert len(result) == 101 and http.get_bytes.await_count == 2
    http.get_bytes.side_effect = None
    http.get_bytes.return_value = b'{"recordsTotal":101,"data":[]}'
    with pytest.raises(ValueError, match="Incomplete"):
        await IbiCameraSource(CONFIGS[1], http).fetch()


@pytest.mark.parametrize(
    "payload", [b"{}", b'{"data":[],"recordsTotal":-1}', b'{"data":[],"recordsTotal":"x"}']
)
async def test_invalid_page_contract(payload):
    http = AsyncMock()
    http.get_bytes.return_value = payload
    with pytest.raises(ValueError):
        await IbiCameraSource(CONFIGS[1], http).fetch()


def test_ontario_uses_enabled_view():
    rows = [
        {
            "Id": 2,
            "Location": "QEW",
            "Latitude": 43,
            "Longitude": -79,
            "Views": [
                {"Status": "Disabled", "Url": "https://511on.ca/old"},
                {"Status": "Enabled", "Url": "https://511on.ca/map/Cctv/2"},
            ],
        }
    ]
    result = parse_index("ontario", "Ontario", "https://511on.ca", rows * 2)
    assert len(result) == 1 and result[0].snapshot_url.endswith("/2")


@pytest.mark.parametrize(
    "provider,row",
    [
        (
            "caltrans",
            {
                "attributes": {
                    "OBJECTID": 1,
                    "locationName": "SR-20",
                    "latitude": 39,
                    "longitude": -123,
                    "currentImageURL": "https://cwwp2.dot.ca.gov/a.jpg",
                }
            },
        ),
        (
            "oregon",
            {
                "attributes": {
                    "cameraId": 1,
                    "title": "US101",
                    "latitude": 45,
                    "longitude": -123,
                    "filename": "camera.jpg",
                }
            },
        ),
        (
            "wsdot",
            {
                "CameraID": 1,
                "Title": "I-5",
                "CameraLocation": {"Latitude": 47, "Longitude": -122},
                "ImageURL": "https://images.wsdot.wa.gov/a.jpg",
            },
        ),
        ("ottawa", {"id": 1, "number": 2, "latitude": 45, "longitude": -75, "description": "Main"}),
        (
            "toronto",
            {
                "properties": {
                    "REC_ID": 1,
                    "MAINROAD": "York",
                    "IMAGEURL": "https://opendata.toronto.ca/a.jpg",
                },
                "geometry": {"coordinates": [[-79, 43]]},
            },
        ),
        (
            "quebec",
            {
                "properties": {"IDEcamera": "1", "DescriptionLocalisationEn": "Quebec"},
                "geometry": {"coordinates": [-71, 46]},
            },
        ),
        (
            "drivebc",
            {
                "id": 1,
                "name": "BC",
                "location": {"coordinates": [-123, 49]},
                "links": {"imageDisplay": "/camera.jpg"},
            },
        ),
        (
            "michigan",
            {
                "county": '<a href="/?lat=43&lon=-85&id=1">Go to</a>',
                "image": '<img src="https://micamerasimages.net/camera.jpg">',
                "route": "I-75",
            },
        ),
        (
            "indiana",
            {
                "__typename": "Camera",
                "active": True,
                "uri": "camera/1",
                "features": [{"geometry": {"coordinates": [-86, 40]}}],
                "views": [{"url": "https://public.carsprogram.org/cameras/IN/INDOT_1_abc.flv.png"}],
            },
        ),
        (
            "montreal",
            {
                "id": 1,
                "name": "A",
                "lat": 45,
                "lng": -73,
                "url": "https://ville.montreal.qc.ca/a.jpg",
            },
        ),
        (
            "illinois",
            {
                "cameraId": 1,
                "cameraName": "A",
                "latitude": 41,
                "longitude": -87,
                "imageUrl": "https://travelmidwest.com/a.jpg",
            },
        ),
    ],
)
def test_official_shapes(provider, row):
    cam = parse_row(provider, provider, "https://example.org", row)
    assert cam and cam.id == provider + ":1"
    if provider in ("indiana", "quebec"):
        assert cam.stream_url and cam.stream_type in ("hls", "mp4")


@pytest.mark.parametrize(
    "provider",
    [
        "caltrans",
        "oregon",
        "wsdot",
        "ottawa",
        "toronto",
        "quebec",
        "drivebc",
        "michigan",
        "indiana",
        "montreal",
        "illinois",
    ],
)
def test_missing_fields_are_skipped(provider):
    assert parse_row(provider, provider, "https://example.org", {}) is None


async def test_empty_and_truncated_index_fail_refresh():
    http = AsyncMock()
    for payload in (b"[]", b'{"exceededTransferLimit":true}', b"{}"):
        http.get_bytes.return_value = payload
        with pytest.raises(ValueError):
            await AmericanCameraSource("caltrans", http).fetch()


async def test_published_links_and_all_sources_registered():
    sources = build_sources(AsyncMock())
    assert len(sources) == 21 and len({source.id for source in sources}) == 21
    links = await AmericanPublishedLinks().fetch()
    assert len(links) == 4
    assert links[2].snapshot_url is None and links[2].external_url
