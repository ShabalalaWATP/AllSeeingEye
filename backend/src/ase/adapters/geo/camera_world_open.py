"""Official keyless camera indexes outside Europe and mainland North America.

Queensland's QLDTraffic web cameras (GeoJSON, CC BY 4.0 on data.qld.gov.au) and Puerto Rico's
Autoridad de Carreteras y Transportacion ITS cameras (a read-only JSON POST the site's own map
makes). See docs/CAMERA_WORLD.md.
"""

import json
from typing import Any
from urllib.parse import urljoin

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_curated import HostPolicy, collect
from ase.adapters.geo.camera_http import CameraHttpClient
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

ENDPOINTS = {
    "queensland": "https://data.qldtraffic.qld.gov.au/webcameras.geojson",
    "puertorico": "https://its.act.pr.gov/es/Default.aspx/GetCctv",
}
NAMES = {
    "queensland": "QLDTraffic (Queensland)",
    "puertorico": "ACT Puerto Rico ITS",
}
PAGES = {"queensland": "https://qldtraffic.qld.gov.au/", "puertorico": "https://its.act.pr.gov/"}
MEDIA_HOSTS = frozenset({"cameras.qldtraffic.qld.gov.au", "its.act.pr.gov"})
POLICY = HostPolicy(MEDIA_HOSTS, frozenset(), MEDIA_HOSTS, NAMES, PAGES)
BOUNDS = {"queensland": (-29.2, -9.0, 137.9, 153.7), "puertorico": (17.8, 18.6, -67.4, -65.2)}


def _within(provider: str, row: dict[str, Any]) -> bool:
    south, north, west, east = BOUNDS[provider]
    try:
        return south <= float(row["lat"]) <= north and west <= float(row["lng"]) <= east
    except (KeyError, TypeError, ValueError):
        return False


def parse_queensland(data: Any) -> list[dict[str, Any]]:
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list):
        raise ValueError("Invalid QLDTraffic camera collection")
    rows = []
    for feature in features[:5000]:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(props, dict) or not isinstance(geometry, dict):
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        rows.append(
            {
                "id": props.get("id"),
                "name": props.get("description"),
                "lat": coordinates[1],
                "lng": coordinates[0],
                "feed_url": props.get("image_url"),
            }
        )
    return rows


def parse_puertorico(data: Any) -> list[dict[str, Any]]:
    # ASP.NET page methods wrap the result as {"d": {"Success": true, "Cctv": [...]}}.
    wrapper = data.get("d") if isinstance(data, dict) else None
    items = wrapper.get("Cctv") if isinstance(wrapper, dict) else None
    if not isinstance(items, list):
        raise ValueError("Invalid Puerto Rico camera list")
    rows = []
    for item in items[:5000]:
        if not isinstance(item, dict) or not isinstance(item.get("ImageUrl"), str):
            continue
        rows.append(
            {
                "id": item.get("Id"),
                "name": item.get("LocationEs") or item.get("Name"),
                "lat": item.get("Latitude"),
                "lng": item.get("Longitude"),
                "feed_url": urljoin("https://its.act.pr.gov/", item["ImageUrl"]),
            }
        )
    return rows


def parse(provider: str, data: Any) -> tuple[Camera, ...]:
    parser = parse_queensland if provider == "queensland" else parse_puertorico
    rows = [row for row in parser(data) if _within(provider, row)]
    cameras = collect(POLICY, provider, rows, approximate=False)
    if not cameras:
        raise ValueError(f"{NAMES[provider]} returned no usable public cameras")
    return cameras


class WorldOpenSource:
    def __init__(self, provider: str, http: FeedHttpClient) -> None:
        self.id, self.name, self.http = provider, NAMES[provider], http

    async def fetch(self) -> tuple[Camera, ...]:
        if self.id == "puertorico":
            if not isinstance(self.http, CameraHttpClient):
                raise ValueError("Puerto Rico cameras need the camera HTTP client")
            return parse(self.id, await self.http.post_json(ENDPOINTS[self.id], {}))
        payload = await self.http.get_bytes(ENDPOINTS[self.id], conditional=False, max_redirects=0)
        return parse(self.id, json.loads(payload))


def build_sources(http: FeedHttpClient) -> tuple[CameraSource, ...]:
    return tuple(WorldOpenSource(provider, http) for provider in ENDPOINTS)
