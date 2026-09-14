"""European map catalogues (KML and WFS) and Queensland and Puerto Rico camera indexes."""

import json
from unittest.mock import AsyncMock

import pytest

from ase.adapters.geo import camera_europe_maps, camera_world_open
from ase.adapters.geo.camera_http import CameraHttpClient

LUXEMBOURG = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark id="camera_3"><name>A6 - Camera 3</name>
<Point><coordinates>5.921276000000001,49.636941,0</coordinates></Point></Placemark>
<Placemark id="icon_9"><name>Not a camera</name>
<Point><coordinates>6,49</coordinates></Point></Placemark>
<Placemark id="camera_4"><name>No point</name></Placemark>
</Document></kml>"""

MADRID = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark>
<description>&lt;div align=center&gt;&lt;img
src=https://informo.madrid.es/cameras/Camara06303.jpg?v=78465  width=300/&gt;
&lt;br/&gt;PLAZA DE CASTILLA&lt;/div&gt;</description>
<ExtendedData><Data name="Numero"><Value>06303</Value></Data>
<Data name="Nombre"><Value>PLAZA DE CASTILLA (NORTE)</Value></Data></ExtendedData>
<Point><coordinates>-3.68894207537291,40.466063829633,10 </coordinates></Point>
</Placemark>
<Placemark>
<description>&lt;img src=https://evil.test/cameras/Camara1.jpg&gt;</description>
<ExtendedData><Data name="Numero"><Value>1</Value></Data></ExtendedData>
<Point><coordinates>-3.7,40.4</coordinates></Point>
</Placemark>
</Document></kml>"""

LYON = {
    "features": [
        {
            "geometry": {"coordinates": [4.81978207, 45.75235833]},
            "properties": {
                "nom": "Lyon - Perrache",
                "libellelong": "Tunnel sous Fourviere",
                "identifiant": 219,
                "url": "https://download.data.grandlyon.com/files/rdata/cam/CWL5801.JPG",
            },
        },
        {"geometry": {"coordinates": [4.8]}, "properties": {"identifiant": 220}},
        "junk",
    ]
}


def test_luxembourg_builds_images_from_camera_ids() -> None:
    (camera,) = camera_europe_maps.parse("luxembourg", LUXEMBOURG)
    assert camera.id == "luxembourg:3" and camera.title == "A6 - Camera 3"
    assert camera.snapshot_url == "https://www.cita.lu/info_trafic/cameras/images/cccam_3.jpg"
    assert (camera.latitude, camera.longitude) == (49.636941, 5.921276000000001)


def test_madrid_reads_the_image_from_escaped_description_on_its_own_host() -> None:
    (camera,) = camera_europe_maps.parse("madrid", MADRID)
    assert camera.id == "madrid:06303" and camera.title == "PLAZA DE CASTILLA (NORTE)"
    assert camera.snapshot_url == "https://informo.madrid.es/cameras/Camara06303.jpg"


def test_lyon_wfs_features() -> None:
    (camera,) = camera_europe_maps.parse("lyon", json.dumps(LYON).encode())
    assert camera.id == "lyon:219" and camera.title == "Lyon - Perrache - Tunnel sous Fourviere"


def test_map_catalogues_reject_bad_payloads() -> None:
    with pytest.raises(ValueError, match="KML"):
        camera_europe_maps.parse("luxembourg", b"not xml")
    with pytest.raises(ValueError, match="Lyon"):
        camera_europe_maps.parse("lyon", b"[]")
    with pytest.raises(ValueError, match="no usable"):
        camera_europe_maps.parse("madrid", b"<kml/>")


async def test_map_sources_fetch_fixed_urls() -> None:
    http = AsyncMock()
    http.get_bytes.return_value = LUXEMBOURG
    sources = camera_europe_maps.build_sources(http)
    assert [source.id for source in sources] == ["luxembourg", "madrid", "lyon"]
    assert len(await sources[0].fetch()) == 1
    http.get_bytes.assert_awaited_once_with(
        camera_europe_maps.ENDPOINTS["luxembourg"], conditional=False, max_redirects=0, accept="*/*"
    )


QUEENSLAND = {
    "features": [
        {
            "geometry": {"coordinates": [153.0086975, -27.5551796]},
            "properties": {
                "id": 1,
                "description": "Archerfield - Ipswich Motorway & Granard Rd - North",
                "image_url": "https://cameras.qldtraffic.qld.gov.au/Metropolitan/Archerfield.jpg",
            },
        },
        {
            "geometry": {"coordinates": [151.2, -33.8]},
            "properties": {"id": 2, "image_url": "https://cameras.qldtraffic.qld.gov.au/x.jpg"},
        },
        {"geometry": {}, "properties": {"id": 3}},
        {"properties": "junk"},
    ]
}
PUERTO_RICO = {
    "d": {
        "Success": True,
        "Cctv": [
            {
                "Id": 12,
                "Name": "18-4.6_04 MD-IPV",
                "LocationEs": "PR-18 Km 4.6 MED",
                "Latitude": 18.389633,
                "Longitude": -66.072539,
                "ImageUrl": "/images/cameras/SJPR18-4-6.jpg",
            },
            {"Id": 13, "Latitude": 18.4, "Longitude": -66.0, "ImageUrl": None},
            {"Id": 14, "Latitude": 40.0, "Longitude": -66.0, "ImageUrl": "/images/cameras/x.jpg"},
        ],
    }
}


def test_queensland_keeps_state_cameras() -> None:
    (camera,) = camera_world_open.parse("queensland", QUEENSLAND)
    assert camera.id == "queensland:1"
    assert camera.snapshot_url.startswith("https://cameras.qldtraffic.qld.gov.au/")
    with pytest.raises(ValueError, match="QLDTraffic"):
        camera_world_open.parse("queensland", [])


def test_puerto_rico_resolves_relative_images_on_its_host() -> None:
    (camera,) = camera_world_open.parse("puertorico", PUERTO_RICO)
    assert camera.id == "puertorico:12" and camera.title == "PR-18 Km 4.6 MED"
    assert camera.snapshot_url == "https://its.act.pr.gov/images/cameras/SJPR18-4-6.jpg"
    for bad in ({}, {"d": []}, {"d": {"Cctv": {}}}):
        with pytest.raises(ValueError, match="Puerto Rico"):
            camera_world_open.parse("puertorico", bad)
    with pytest.raises(ValueError, match="no usable"):
        camera_world_open.parse("puertorico", {"d": {"Cctv": []}})


async def test_world_sources_use_fixed_requests() -> None:
    http = AsyncMock()
    http.get_bytes.return_value = json.dumps(QUEENSLAND).encode()
    queensland, puertorico = camera_world_open.build_sources(http)
    assert len(await queensland.fetch()) == 1
    http.get_bytes.assert_awaited_once_with(
        camera_world_open.ENDPOINTS["queensland"], conditional=False, max_redirects=0
    )
    with pytest.raises(ValueError, match="camera HTTP client"):
        await puertorico.fetch()
    client = AsyncMock(spec=CameraHttpClient)
    client.post_json.return_value = PUERTO_RICO
    source = camera_world_open.WorldOpenSource("puertorico", client)
    assert len(await source.fetch()) == 1
    client.post_json.assert_awaited_once_with(camera_world_open.ENDPOINTS["puertorico"], {})
