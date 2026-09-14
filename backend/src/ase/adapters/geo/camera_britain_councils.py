"""UK council camera catalogues fetched from fixed public pages. See docs/CAMERA_EUROPE.md.

North East Traffic Cameras (the Tyne and Wear UTMC site), North Yorkshire Council and
Westmorland and Furness Council road weather cameras, and Derbyshire County Council traffic
cameras. HTML pages are parsed for data only and never rendered. Durham UTMC cameras listed by
the North East site are skipped because the Durham provider already carries them.
"""

import json
import re
import time
from collections.abc import Callable
from html import unescape
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_curated import HostPolicy, collect
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

NE_BASE = "https://netrafficcams.co.uk"
ENDPOINTS = {
    "northeast": (f"{NE_BASE}/map", f"{NE_BASE}/all-cameras?items_per_page=All"),
    "northyorkshire": ("https://www.northyorks.gov.uk/nycc_weather_cameras/markers",),
    "westmorland": (
        "https://www.westmorlandandfurness.gov.uk/parking-streets-and-transport/"
        "streets-roads-and-pavements/weather-cameras",
    ),
    "derbyshire": (
        "https://apps.derbyshire.gov.uk/applications/traffic-cameras/camera-locations.asp",
    ),
}
NAMES = {
    "northeast": "North East Traffic Cameras (Tyne and Wear UTMC)",
    "northyorkshire": "North Yorkshire Council weather cameras",
    "westmorland": "Westmorland and Furness Council weather cameras",
    "derbyshire": "Derbyshire County Council traffic cameras",
}
PAGES = {provider: urls[0] for provider, urls in ENDPOINTS.items()}
PAGES["northeast"] = f"{NE_BASE}/all-cameras"
MEDIA_HOSTS = frozenset(
    {
        "netrafficcams.co.uk",
        "www.northyorks.gov.uk",
        "www.westmorlandandfurness.gov.uk",
        "apps.derbyshire.gov.uk",
    }
)
POLICY = HostPolicy(MEDIA_HOSTS, frozenset(), MEDIA_HOSTS, NAMES, PAGES)
NE_SETTINGS = re.compile(
    rb'<script type="application/json" data-drupal-selector="drupal-settings-json">(.*?)</script>',
    re.S,
)
NE_ITEM = re.compile(
    r'<a href="/node/(\d{1,8})" hreflang="en">([^<]{1,200})</a>.*?'
    r'<img[^>]*src="(/sites/default/files/images/cameras/([A-Za-z0-9_.-]{1,80}\.jpg)'
    r'\?mtime=(\d{9,11}))"',
    re.S,
)
NE_MAX_AGE_SECONDS = 24 * 3600
WF_STATIONS = re.compile(rb"data-stations='([^']{2,200000})'")
DERBYSHIRE_PHOTO = re.compile(r"/external-assets/images/traffic-cameras/originals/[\w-]{1,40}\.jpg")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_northeast(map_page: bytes, list_page: bytes, now: float) -> list[dict[str, Any]]:
    """Positions from the map's Leaflet settings, images from the camera list, joined by node."""
    settings = NE_SETTINGS.search(map_page)
    if settings is None:
        raise ValueError("North East camera map settings missing")
    leaflet = _dict(_dict(json.loads(settings.group(1))).get("leaflet"))
    positions: dict[str, tuple[Any, Any]] = {}
    for view in leaflet.values():
        for feature in map(_dict, _dict(view).get("features") or []):
            positions[str(feature.get("entity_id"))] = (feature.get("lat"), feature.get("lon"))
    rows = []
    for node, title, path, filename, mtime in NE_ITEM.findall(list_page.decode("utf-8", "replace")):
        if filename.startswith("dutmc_") or now - int(mtime) > NE_MAX_AGE_SECONDS:
            continue
        if node not in positions:
            continue
        lat, lon = positions[node]
        rows.append(
            {
                "id": node,
                "name": unescape(title),
                "lat": lat,
                "lng": lon,
                "feed_url": NE_BASE + path.split("?", 1)[0],
                "external_url": f"{NE_BASE}/node/{node}",
            }
        )
    return rows


def parse_northyorkshire(payload: bytes) -> list[dict[str, Any]]:
    rows = []
    for feature in map(_dict, _dict(json.loads(payload)).get("features") or []):
        props, geometry = _dict(feature.get("properties")), _dict(feature.get("geometry"))
        link, coordinates = props.get("Weblink"), geometry.get("coordinates")
        if props.get("ErrorStatus") != "Ok" or not isinstance(coordinates, list):
            continue
        match = re.fullmatch(r"/nycc_weather_cameras/cameras/(\d{1,8})(&cam=\d)?", str(link))
        if match is None or len(coordinates) < 2:
            continue
        rows.append(
            {
                "id": match.group(1) + (match.group(2) or "").replace("&cam=", "-"),
                "name": props.get("Name"),
                "lat": coordinates[1],
                "lng": coordinates[0],
                "feed_url": "https://www.northyorks.gov.uk" + str(link),
            }
        )
    return rows


def parse_westmorland(payload: bytes) -> list[dict[str, Any]]:
    match = WF_STATIONS.search(payload)
    if match is None:
        raise ValueError("Westmorland and Furness station list missing")
    rows = []
    for station in map(_dict, json.loads(unescape(match.group(1).decode("utf-8", "replace")))):
        key = str(station.get("id"))
        if not key.isdigit():
            continue
        rows.append(
            {
                "id": key,
                "name": station.get("name"),
                "lat": station.get("lat"),
                "lng": station.get("lng"),
                "feed_url": "https://www.westmorlandandfurness.gov.uk/sites/default/files/weather/"
                f"vaisalacamera{key}_0.jpg",
            }
        )
    return rows


def parse_derbyshire(payload: bytes) -> list[dict[str, Any]]:
    """The council publishes GeoJSON-shaped data with coordinates in latitude, longitude order."""
    rows = []
    for index, feature in enumerate(map(_dict, _dict(json.loads(payload)).get("features") or [])):
        props, geometry = _dict(feature.get("properties")), _dict(feature.get("geometry"))
        coordinates, photo = (
            geometry.get("coordinates"),
            DERBYSHIRE_PHOTO.match(str(props.get("Photo"))),
        )
        if not isinstance(coordinates, list) or len(coordinates) < 2 or photo is None:
            continue
        rows.append(
            {
                "id": photo.group(0).rsplit("/", 1)[1].removesuffix(".jpg") or index,
                "name": unescape(str(props.get("Title") or "")),
                "lat": coordinates[0],
                "lng": coordinates[1],
                "feed_url": "https://apps.derbyshire.gov.uk" + photo.group(0),
            }
        )
    return rows


UK_BOUNDS = (49.8, 61.0, -8.7, 1.9)


def parse(provider: str, pages: list[bytes], now: float) -> tuple[Camera, ...]:
    parsers: dict[str, Callable[[], list[dict[str, Any]]]] = {
        "northeast": lambda: parse_northeast(pages[0], pages[1], now),
        "northyorkshire": lambda: parse_northyorkshire(pages[0]),
        "westmorland": lambda: parse_westmorland(pages[0]),
        "derbyshire": lambda: parse_derbyshire(pages[0]),
    }
    south, north, west, east = UK_BOUNDS
    rows = []
    for row in parsers[provider]():
        try:
            inside = south <= float(row["lat"]) <= north and west <= float(row["lng"]) <= east
        except (TypeError, ValueError):
            inside = False
        if inside:
            rows.append(row | {"source": NAMES[provider]})
    cameras = collect(POLICY, provider, rows, approximate=False)
    if not cameras:
        raise ValueError(f"{NAMES[provider]} returned no usable public cameras")
    return cameras


class CouncilCameraSource:
    def __init__(self, provider: str, http: FeedHttpClient, clock: Callable[[], float] = time.time):
        self.id, self.name, self.http, self.clock = provider, NAMES[provider], http, clock

    async def fetch(self) -> tuple[Camera, ...]:
        pages = [
            await self.http.get_bytes(url, conditional=False, max_redirects=0, accept="*/*")
            for url in ENDPOINTS[self.id]
        ]
        return parse(self.id, pages, self.clock())


def build_sources(http: FeedHttpClient) -> tuple[CameraSource, ...]:
    return tuple(CouncilCameraSource(provider, http) for provider in ENDPOINTS)
