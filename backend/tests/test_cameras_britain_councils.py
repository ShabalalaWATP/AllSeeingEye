"""UK council camera catalogues: page parsing, freshness, host policy and fixed requests."""

import json
from unittest.mock import AsyncMock

import pytest

from ase.adapters.geo.camera_britain_councils import (
    ENDPOINTS,
    NE_MAX_AGE_SECONDS,
    CouncilCameraSource,
    build_sources,
    parse,
)

NOW = 1_789_430_000.0
NE_ITEM = (
    '<a href="/node/{node}" hreflang="en">{title}</a> <div><img loading="lazy" '
    'src="/sites/default/files/images/cameras/{file}?mtime={mtime}" /></div>'
)


def northeast_pages() -> list[bytes]:
    settings = {
        "leaflet": {
            "leaflet-map-view-map-page-1": {
                "features": [
                    {"lat": 54.97, "lon": -1.61, "entity_id": "700"},
                    {"lat": 54.75, "lon": -1.59, "entity_id": "644"},
                    {"lat": 54.9, "lon": -1.5, "entity_id": "701"},
                ]
            }
        }
    }
    map_page = (
        '<html><script type="application/json" data-drupal-selector="drupal-settings-json">'
        + json.dumps(settings)
        + "</script></html>"
    ).encode()
    fresh, stale = int(NOW - 60), int(NOW - NE_MAX_AGE_SECONDS - 5)
    list_page = "".join(
        [
            NE_ITEM.format(
                node=700, title="A186 Westgate Rd &amp; Barrack Rd", file="NC_A1.jpg", mtime=fresh
            ),
            NE_ITEM.format(node=644, title="Durham copy", file="dutmc_11.jpg", mtime=fresh),
            NE_ITEM.format(node=999, title="No position", file="GH_1.jpg", mtime=fresh),
            NE_ITEM.format(node=701, title="Stale", file="SL_2.jpg", mtime=stale),
        ]
    ).encode()
    return [map_page, list_page]


def test_northeast_joins_positions_skips_durham_stale_and_unplaced() -> None:
    (camera,) = parse("northeast", northeast_pages(), NOW)
    assert camera.id == "northeast:700"
    assert camera.title == "A186 Westgate Rd & Barrack Rd"
    assert camera.snapshot_url == (
        "https://netrafficcams.co.uk/sites/default/files/images/cameras/NC_A1.jpg"
    )
    assert camera.external_url == "https://netrafficcams.co.uk/node/700"
    assert (camera.latitude, camera.longitude) == (54.97, -1.61)
    with pytest.raises(ValueError, match="settings missing"):
        parse("northeast", [b"<html></html>", b""], NOW)


def feature(coordinates: list[float], **properties: object) -> dict[str, object]:
    return {"geometry": {"coordinates": coordinates}, "properties": properties}


def test_north_yorkshire_keeps_working_cameras_and_second_views() -> None:
    data = {
        "features": [
            feature(
                [-0.663957, 54.441663],
                Weblink="/nycc_weather_cameras/cameras/10888&cam=2",
                Name="Blue Bank uphill",
                ErrorStatus="Ok",
            ),
            feature(
                [-1.40497, 54.223399],
                Weblink="/nycc_weather_cameras/cameras/3880",
                Name="Broken",
                ErrorStatus="Error",
            ),
            feature([-1.4, 54.2], Weblink="https://evil.test/x.jpg", ErrorStatus="Ok"),
        ]
    }
    (camera,) = parse("northyorkshire", [json.dumps(data).encode()], NOW)
    assert camera.id == "northyorkshire:10888-2"
    assert camera.snapshot_url == (
        "https://www.northyorks.gov.uk/nycc_weather_cameras/cameras/10888&cam=2"
    )


def test_westmorland_builds_images_from_station_ids() -> None:
    stations = [
        {"id": "11827", "name": "A5086 Arlecdon", "lat": 54.553348, "lng": -3.4778347},
        {"id": "x", "lat": 54, "lng": -3},
    ]
    encoded = json.dumps(stations).replace('"', "&quot;")
    page = f"<div data-stations='{encoded}'></div>".encode()
    (camera,) = parse("westmorland", [page], NOW)
    assert str(camera.snapshot_url).endswith("/weather/vaisalacamera11827_0.jpg")
    with pytest.raises(ValueError, match="station list missing"):
        parse("westmorland", [b"<div></div>"], NOW)


def test_derbyshire_reads_latitude_first_coordinates() -> None:
    photo = "/external-assets/images/traffic-cameras/originals/34_cam1.jpg"
    data = {
        "features": [
            feature([53.295708, -1.196501], Photo=photo + "?version=x", Title="Whitwell A619"),
            feature([53.2, -1.1], Photo="https://evil.test/a.jpg"),
        ]
    }
    (camera,) = parse("derbyshire", [json.dumps(data).encode()], NOW)
    assert (camera.latitude, camera.longitude) == (53.295708, -1.196501)
    assert camera.snapshot_url == "https://apps.derbyshire.gov.uk" + photo


def test_positions_outside_the_uk_and_empty_catalogues_fail() -> None:
    photo = "/external-assets/images/traffic-cameras/originals/1_cam1.jpg"
    data = {"features": [feature([10.0, 10.0], Photo=photo)]}
    with pytest.raises(ValueError, match="no usable"):
        parse("derbyshire", [json.dumps(data).encode()], NOW)


async def test_sources_fetch_their_fixed_pages_in_order() -> None:
    http = AsyncMock()
    http.get_bytes.side_effect = northeast_pages()
    source = CouncilCameraSource("northeast", http, clock=lambda: NOW)
    assert len(await source.fetch()) == 1
    calls = http.get_bytes.await_args_list
    assert [call.args[0] for call in calls] == list(ENDPOINTS["northeast"])
    assert calls[0].kwargs == {"conditional": False, "max_redirects": 0, "accept": "*/*"}
    assert [source.id for source in build_sources(http)] == list(ENDPOINTS)
