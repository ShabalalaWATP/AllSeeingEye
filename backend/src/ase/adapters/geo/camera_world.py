"""Fixed Asia/Pacific transport indexes and public world webcam catalogues.

OSIRIS source attribution and catalogue limitations: docs/CAMERA_WORLD.md.
"""

import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from defusedxml.ElementTree import fromstring

from ase.adapters.feeds.http import FeedHttpClient
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

MEDIA_HOSTS = frozenset(
    {
        "webcams.transport.nsw.gov.au",
        "trafficnz.info",
        "images.data.gov.sg",
        "cam.river.go.jp",
        *(f"cctv-ss{i:02}.thb.gov.tw" for i in range(1, 8)),
    }
)
FRAME_HOSTS = frozenset({"www.youtube.com"})
ENDPOINTS = {
    "australia": "https://www.livetraffic.com/datajson/all-feeds-web.json",
    "newzealand": "https://trafficnz.info/service/traffic/rest/4/cameras/all",
    "taiwan": "https://thbapp.thb.gov.tw/services/cctv/thb",
    "singapore": "https://api.data.gov.sg/v1/transport/traffic-images",
}
NAMES = {
    "australia": "Transport for NSW",
    "newzealand": "NZTA Waka Kotahi",
    "taiwan": "Taiwan Highway Bureau",
    "singapore": "Singapore LTA",
    "japan": "Japan public webcams and MLIT rivers",
    "thailand": "Thailand public webcam streams",
    "taiwan-live": "Taiwan public webcam streams",
    "middle-east": "Middle East public webcam streams",
    "asia-live": "SkylineWebcams Asia",
    "latam-live": "SkylineWebcams Latin America",
    "africa-live": "SkylineWebcams Africa",
    "europe-live": "SkylineWebcams Europe",
}


BOUNDS = {"newzealand": (-47.5, -34, 166, 179), "taiwan": (21, 26.5, 118, 123)}


def media_url(value: Any, hosts: frozenset[str] = MEDIA_HOSTS) -> str | None:
    """Only exact approved HTTPS origins; no credential or port tricks."""
    if not isinstance(value, str) or len(value) > 2048:
        return None
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme == "https" and parts.netloc in hosts and not parts.fragment:
            return value
    except ValueError:
        pass
    return None


def make_camera(provider: str, row: dict[str, Any]) -> Camera | None:
    """Validate upstream geometry and media, preserving supplied location precision."""
    try:
        lat, lon = float(row.get("lat", "")), float(row.get("lng", ""))
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    bounds = BOUNDS.get(provider)
    if bounds and not (bounds[0] <= lat <= bounds[1] and bounds[2] <= lon <= bounds[3]):
        return None
    key = str(row.get("id") or "")
    if not key or len(key) > 160:
        return None
    image = media_url(row.get("feed_url"))
    stream = media_url(row.get("stream_url"), FRAME_HOSTS)
    if stream and re.fullmatch(r"/embed/[A-Za-z0-9_-]{11}", urlsplit(stream).path) is None:
        stream = None
    external = media_url(
        row.get("external_url"),
        frozenset(
            {
                "www.skylinewebcams.com",
                "www.youtube.com",
                "trafficnz.info",
                "www.livetraffic.com",
                "opencctv.org",
            }
        ),
    )
    if not (image or stream or external):
        return None
    source = external or ENDPOINTS.get(provider) or stream or "https://www.river.go.jp/"
    return Camera(
        id=f"{provider}:{key}",
        provider=provider,
        title=str(row.get("name") or NAMES[provider])[:240],
        latitude=lat,
        longitude=lon,
        snapshot_url=image,
        source_url=source,
        attribution=str(row.get("source") or NAMES[provider])[:200]
        + ". Provider terms apply. Catalogue availability does not verify current playback.",
        stream_url=stream,
        stream_type="iframe" if stream else None,
        external_url=external or stream,
        coordinate_precision="approximate" if row.get("approximate") else "exact",
    )


def _collect(provider: str, rows: list[dict[str, Any]]) -> tuple[Camera, ...]:
    cameras = (make_camera(provider, row) for row in rows[:5000])
    return tuple({c.id: c for c in cameras if c is not None}.values())


def parse_australia(payload: bytes) -> tuple[Camera, ...]:
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("Invalid NSW camera catalogue")
    rows = []
    for item in data[:5000]:
        if not isinstance(item, dict) or item.get("eventType") != "liveCams":
            continue
        coords = (item.get("geometry") or {}).get("coordinates")
        props = item.get("properties") or {}
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        rows.append(
            {
                "id": item.get("path"),
                "name": props.get("title"),
                "lat": coords[1],
                "lng": coords[0],
                "feed_url": props.get("href"),
            }
        )
    return _collect("australia", rows)


def parse_newzealand(payload: bytes) -> tuple[Camera, ...]:
    rows: list[dict[str, Any]] = []
    for item in fromstring(payload).iter("camera"):
        if len(rows) >= 5000:
            break
        if item.findtext("offline") == "true" or item.findtext("underMaintenance") == "true":
            continue
        image = item.findtext("imageUrl") or ""
        if not image:
            continue
        rows.append(
            {
                "id": item.findtext("id"),
                "name": item.findtext("name"),
                "lat": item.findtext("latitude"),
                "lng": item.findtext("longitude"),
                "feed_url": urljoin("https://trafficnz.info/", image),
            }
        )
    return _collect("newzealand", rows)


def parse_taiwan(payload: bytes) -> tuple[Camera, ...]:
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("Invalid Taiwan camera catalogue")
    rows = [
        {
            "id": item.get("id") or item.get("stakenumber"),
            "name": item.get("stakenumber"),
            "lat": item.get("gisy"),
            "lng": item.get("gisx"),
            "feed_url": str(item.get("html") or "").rstrip("/") + "/snapshot",
        }
        for item in data[:5000]
        if isinstance(item, dict)
    ]
    return _collect("taiwan", rows)


def parse_singapore(payload: bytes) -> tuple[Camera, ...]:
    data = json.loads(payload)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise ValueError("Invalid Singapore camera catalogue")
    rows = []
    for item in items[0].get("cameras", [])[:5000]:
        if not isinstance(item, dict):
            continue
        location = item.get("location") or {}
        rows.append(
            {
                "id": item.get("camera_id"),
                "name": f"LTA camera {item.get('camera_id')}",
                "lat": location.get("latitude"),
                "lng": location.get("longitude"),
                "feed_url": item.get("image"),
            }
        )
    return _collect("singapore", rows)


@dataclass
class WorldCameraSource:
    id: str
    name: str
    http: FeedHttpClient
    parser: Callable[[bytes], tuple[Camera, ...]]

    async def fetch(self) -> tuple[Camera, ...]:
        payload = await self.http.get_bytes(ENDPOINTS[self.id], conditional=False, max_redirects=0)
        return self.parser(payload)


@dataclass
class CuratedWorldSource:
    id: str
    name: str
    cameras: tuple[Camera, ...]

    async def fetch(self) -> tuple[Camera, ...]:
        return self.cameras


def build_sources(http: FeedHttpClient) -> tuple[CameraSource, ...]:
    parsers = {
        "australia": parse_australia,
        "newzealand": parse_newzealand,
        "taiwan": parse_taiwan,
        "singapore": parse_singapore,
    }
    sources: list[CameraSource] = [
        WorldCameraSource(p, NAMES[p], http, fn) for p, fn in parsers.items()
    ]
    records = json.loads(Path(__file__).with_name("camera_world_catalogue.json").read_text("utf8"))
    for provider in NAMES.keys() - parsers.keys():
        rows = [{**row, "approximate": True} for row in records if row["provider"] == provider]
        # Skyline's poster images can be years old and require hotlink bypass.
        # Preserve the public operator page, never present those posters as live.
        if provider.endswith("live") and provider != "taiwan-live":
            rows = [{**row, "feed_url": None} for row in rows]
        sources.append(CuratedWorldSource(provider, NAMES[provider], _collect(provider, rows)))
    return tuple(sources)
