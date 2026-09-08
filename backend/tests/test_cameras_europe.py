"""Deterministic public catalogue and media boundary regressions."""

import json
from unittest.mock import AsyncMock

import pytest

from ase.adapters.geo.camera_europe import (
    COUNTRIES,
    ENDPOINTS,
    EuropeanCameraSource,
    build_sources,
    curated,
    make_camera,
    parse_index,
)


@pytest.mark.parametrize("provider", [*COUNTRIES, "greece"])
def test_curated_catalogues_keep_media_and_provenance(provider):
    cameras = curated(provider)
    assert cameras
    assert len({c.id for c in cameras}) == len(cameras)
    assert all(c.coordinate_precision == "approximate" for c in cameras)
    assert all(c.snapshot_url or c.stream_url or c.external_url for c in cameras)
    assert all("availability not verified" in c.attribution for c in cameras)
    # Catalogue posters must not be misrepresented as fresh camera snapshots.
    assert not any(c.snapshot_url and "skyline" in c.snapshot_url for c in cameras)


def test_all_assigned_sources_accounted_for():
    sources = build_sources(AsyncMock())
    assert len(sources) == 18
    assert len({s.id for s in sources}) == 18


@pytest.mark.parametrize(
    "url",
    [
        "http://ls.tkchopin.pl/live/a.m3u8",
        "https://localhost/x",
        "https://127.0.0.1/x",
        "https://ls.tkchopin.pl.evil.test/x",
        "https://user@ls.tkchopin.pl/x",
        "https://ls.tkchopin.pl:444/x",
        "https://ls.tkchopin.pl/x#fragment",
        "https://ls.tkchopin.pl/x\n",
    ],
)
def test_rejects_unapproved_media(url):
    assert (
        make_camera(
            "poland",
            {"id": "a", "lat": 54, "lng": 18, "stream_url": url, "stream_type": "hls"},
            approximate=True,
        )
        is None
    )


@pytest.mark.parametrize("lat,lon", [(None, 1), ("nan", 1), (91, 1), (1, 181), (0, 0)])
def test_rejects_invalid_coordinates(lat, lon):
    assert (
        make_camera(
            "x",
            {"id": "a", "lat": lat, "lng": lon, "feed_url": "https://www.vegagerdin.is/x.jpg"},
            approximate=False,
        )
        is None
    )


def test_rws_official_player_is_external_not_image():
    result = parse_index(
        "netherlands",
        json.dumps(
            [
                {
                    "id": 4,
                    "latitude": "52.185241",
                    "longitude": "5.41449",
                    "road": "A1",
                    "stream_url": "https://stream.inmoves.nl/62/embed",
                    "static_url": "https://stream.inmoves.nl/62",
                },
                {},
                "invalid",
            ]
        ).encode(),
    )
    assert len(result) == 1
    assert result[0].snapshot_url is None
    assert result[0].stream_type is None
    assert result[0].external_url == "https://stream.inmoves.nl/62/embed"
    assert result[0].coordinate_precision == "exact"


def test_iceland_relative_images_and_dgt_schema():
    result = parse_index(
        "iceland",
        json.dumps(
            [
                {
                    "Maelist_nr": 7,
                    "Breidd": 64,
                    "Lengd": -21,
                    "Slod": "/vgdata/vefmyndavelar/test.jpg",
                    "Myndavel": "Test",
                },
            ]
        ).encode(),
    )
    assert result[0].snapshot_url == "https://www.vegagerdin.is/vgdata/vefmyndavelar/test.jpg"
    result = parse_index(
        "spain-dgt",
        json.dumps(
            {
                "camaras": [
                    {
                        "id": "2",
                        "latitud": "42",
                        "longitud": "-4",
                        "imagen": "https://etraffic.dgt.es/camarasEtraffic/2.jpg",
                    },
                ]
            }
        ).encode(),
    )
    assert len(result) == 1


def test_catalogue_rejects_wrong_shape_and_bounds_work():
    with pytest.raises(ValueError):
        parse_index("iceland", b"{}")
    row = {
        "id": "1",
        "latitud": "42",
        "longitud": "-4",
        "imagen": "https://etraffic.dgt.es/camarasEtraffic/2.jpg",
    }
    data = {"camaras": [row] * 5000 + [{**row, "id": "too-far"}]}
    assert len(parse_index("spain-dgt", json.dumps(data).encode())) == 1


async def test_fixed_fetch_is_unconditional_without_credentials_or_redirects():
    http = AsyncMock()
    http.get_bytes.return_value = b"[]"
    with pytest.raises(ValueError, match="no supported"):
        await EuropeanCameraSource("asfinag", http).fetch()
    http.get_bytes.assert_awaited_once_with(
        ENDPOINTS["asfinag"], conditional=False, max_redirects=0
    )
    with pytest.raises(ValueError, match="removed Turkish"):
        await EuropeanCameraSource("turkey", http).fetch()
    assert await EuropeanCameraSource("poland", http).fetch()
