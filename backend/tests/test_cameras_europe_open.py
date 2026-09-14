"""Official European JSON camera indexes: parsing, host policy, freshness and fixed requests."""

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from ase.adapters.geo import camera_http
from ase.adapters.geo.camera_europe_open import (
    ENDPOINTS,
    HUNGARY_FRESH_MS,
    OpenEuropeSource,
    build_sources,
    lks94_to_wgs84,
    parse,
    parse_hungary,
)
from ase.adapters.geo.camera_http import CameraHttpClient


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        ((576154, 6056867), (54.64255090647258, 25.179815878771716)),
        ((300000, 6200000), (55.89269901974383, 20.802096216004667)),
        ((650000, 5990000), (54.02565759373221, 26.28948413135793)),
    ],
)
def test_lks94_matches_proj_reference(point, expected) -> None:
    lat, lon = lks94_to_wgs84(*point)
    assert lat == pytest.approx(expected[0], abs=1e-7)
    assert lon == pytest.approx(expected[1], abs=1e-7)


def test_lithuania_converts_grid_positions_and_keeps_its_image_host() -> None:
    rows = [
        {
            "id": 72,
            "name": "Vilnius A1 10,04",
            "image": "https://eismoinfo.lt/eismoinfo-backend/image-provider/camera/last?id=72",
            "x": 576154,
            "y": 6056867,
        },
        {"id": 73, "name": "Outside", "image": "https://eismoinfo.lt/x", "x": 0, "y": 0},
        {"id": 74, "name": "Bad", "image": "https://eismoinfo.lt/x", "x": "east"},
        {"id": 75, "name": "Elsewhere", "image": "https://evil.test/x", "x": 576154, "y": 6056867},
    ]
    cameras = parse("lithuania", json.dumps(rows).encode())
    assert [camera.id for camera in cameras] == ["lithuania:72"]
    assert cameras[0].latitude == pytest.approx(54.6426, abs=1e-4)
    assert cameras[0].coordinate_precision == "exact"


def test_ireland_uses_public_still_views() -> None:
    rows = [
        {
            "id": 91,
            "public": True,
            "name": "Reaghstown",
            "location": {"latitude": 53.929722, "longitude": -6.648056},
            "views": [
                {
                    "name": "N2 Reaghstown",
                    "type": "STILL_IMAGE",
                    "url": "https://irecam.carsprogram.org/a.jpeg",
                },
                {"name": "Video", "type": "VIDEO", "url": "https://irecam.carsprogram.org/b"},
            ],
        },
        {"id": 92, "public": False, "location": {}, "views": []},
    ]
    cameras = parse("ireland", json.dumps(rows).encode())
    assert [(camera.id, camera.title) for camera in cameras] == [("ireland:91-0", "N2 Reaghstown")]


def test_norway_keeps_ok_cameras_and_their_streams() -> None:
    data = {
        "features": [
            {
                "geometry": {"coordinates": [24.10096, 70.27835]},
                "properties": {
                    "name": "Aisaroaivi",
                    "cameras": [
                        {
                            "id": "2000065_1",
                            "orientationDescription": "Skaidi",
                            "stillImageUrl": "https://kamera.atlas.vegvesen.no/api/images/2000065_1",
                            "videoUrl": "https://kamera.vegvesen.no/public/2000065_1/manifest.m3u8",
                            "status": "OK",
                        },
                        {
                            "id": "2000065_2",
                            "stillImageUrl": "https://kamera.atlas.vegvesen.no/x",
                            "status": "EXPIRED",
                        },
                    ],
                },
            },
            {"geometry": {"coordinates": []}, "properties": {"cameras": [{"status": "OK"}]}},
        ]
    }
    (camera,) = parse("norway", json.dumps(data).encode())
    assert camera.title == "Aisaroaivi (towards Skaidi)"
    assert camera.stream_type == "hls" and camera.stream_url.endswith("manifest.m3u8")
    assert (camera.latitude, camera.longitude) == (70.27835, 24.10096)


def hungary(last: float, **webcam: object) -> dict[str, object]:
    return {
        "features": [
            {
                "geometry": {"coordinates": [21.1167, 47.3178]},
                "properties": {
                    "placeName": "Puspokladany",
                    "active": True,
                    "published": True,
                    "webcams": [
                        {
                            "cameraPlaceId": "mcs217",
                            "cameraNum": 3,
                            "cameraView": "Budapest",
                            "published": True,
                            "lastImage": last,
                            **webcam,
                        }
                    ],
                },
            }
        ]
    }


def test_hungary_builds_image_urls_only_for_fresh_published_cameras() -> None:
    now = 1_789_417_217_506
    (row,) = parse_hungary(hungary(now - 1000), now)
    assert row["feed_url"] == "https://cdnuiwebcams.utinform.hu/webcamimages/mcs217_3.jpg"
    assert row["name"] == "Puspokladany (towards Budapest)"
    assert parse_hungary(hungary(now - HUNGARY_FRESH_MS - 1), now) == []
    assert parse_hungary(hungary(now, published=False), now) == []
    assert parse_hungary(hungary(now, cameraPlaceId="../x"), now) == []
    assert parse_hungary(hungary(now, cameraNum="3"), now) == []


def test_autostrade_stills_and_clips_from_fixed_prefixes() -> None:
    data = {
        "webcams": [
            {
                "c_tel": 301,
                "t_des_pub": "A14 km. 225,1 Ancona Nord",
                "n_crd_lat": 43.56073,
                "n_crd_lon": 13.46768,
                "frames": {
                    "F_0": {"t_url": "dt7/a-3-0.jpg"},
                    "T": {"t_url": "dt7/a-3-thumb.jpg"},
                    "V": {"t_url": "dt7/a-3.mp4"},
                },
            },
            {
                "c_tel": 302,
                "n_crd_lat": 44,
                "n_crd_lon": 11,
                "frames": {"T": {"t_url": "dt7/b-thumb.jpg"}},
            },
            {
                "c_tel": 303,
                "n_crd_lat": 44,
                "n_crd_lon": 11,
                "frames": {"F_0": {"t_url": "../x.jpg"}},
            },
        ]
    }
    first, second = parse("autostrade", json.dumps(data).encode())
    assert first.snapshot_url == "https://video.autostrade.it/video-frames/dt7/a-3-0.jpg"
    assert first.stream_url == "https://video.autostrade.it/video-mp4_hq/dt7/a-3.mp4"
    assert first.stream_type == "mp4"
    assert second.snapshot_url.endswith("b-thumb.jpg") and second.stream_url is None


def test_empty_catalogues_fail_the_refresh() -> None:
    for provider, payload in [
        ("lithuania", b"[]"),
        ("ireland", b"{}"),
        ("norway", b"{}"),
        ("hungary", b'{"features": 1}'),
        ("autostrade", b"[]"),
    ]:
        with pytest.raises(ValueError, match="no usable"):
            parse(provider, payload)


async def test_sources_use_fixed_urls_and_norway_identifies_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http = AsyncMock()
    http.get_bytes.return_value = json.dumps(
        [{"id": 1, "image": "https://eismoinfo.lt/i?id=1", "x": 576154, "y": 6056867}]
    ).encode()
    assert len(await OpenEuropeSource("lithuania", http).fetch()) == 1
    http.get_bytes.assert_awaited_once_with(
        ENDPOINTS["lithuania"], conditional=False, max_redirects=0
    )
    with pytest.raises(ValueError, match="camera HTTP client"):
        await OpenEuropeSource("norway", http).fetch()
    assert [source.id for source in build_sources(http)] == list(ENDPOINTS)

    monkeypatch.setattr(camera_http, "assert_public_host", AsyncMock(return_value=None))
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=b'{"features": []}')

    client = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ValueError, match="no usable"):
        await OpenEuropeSource("norway", client).fetch()
    assert seen[0].headers["x-system-id"] == "theallseeingeye"
    assert str(seen[0].url) == ENDPOINTS["norway"]
    with pytest.raises(ValueError, match="identifier"):
        await client.get_identified(ENDPOINTS["norway"], "bad value")

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400)

    refusing = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(refuse))
    )
    with pytest.raises(camera_http.FeedFetchError, match="refused"):
        await refusing.get_identified(ENDPOINTS["norway"], "theallseeingeye")

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    failing = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(broken))
    )
    with pytest.raises(camera_http.FeedFetchError, match="request failed"):
        await failing.get_identified(ENDPOINTS["norway"], "theallseeingeye")
