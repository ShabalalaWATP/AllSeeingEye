"""Official keyless camera indexes. URLs are source constants, never caller supplied."""

import json
import math
import re
from typing import Any
from urllib.parse import urlsplit
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.domain.cameras import Camera, CameraProviderId

ENDPOINTS = {
    "tfl": "https://api.tfl.gov.uk/Place/Type/JamCam",
    "hongkong": "https://static.data.gov.hk/td/traffic-snapshot-images/code/Traffic_Camera_Locations_En.xml",
    "fintraffic": "https://tie.digitraffic.fi/api/weathercam/v1/stations",
}
NAMES = {
    "tfl": "Transport for London",
    "hongkong": "Hong Kong Transport Department",
    "fintraffic": "Fintraffic",
}
SOURCES = {
    "tfl": "https://tfl.gov.uk/info-for/open-data-users/",
    "hongkong": "https://data.gov.hk/en-data/dataset/hk-td-tis_1-traffic-snapshot-images",
    "fintraffic": "https://www.digitraffic.fi/en/road-traffic/",
}
ATTRIBUTION = {
    "tfl": "Powered by TfL Open Data. Contains OS data © Crown copyright and database rights.",
    "hongkong": (
        "Traffic snapshot images © Hong Kong Transport Department. DATA.GOV.HK terms apply."
    ),
    "fintraffic": "Source: Fintraffic / Digitraffic. Creative Commons Attribution 4.0.",
}
IMAGE_PATHS = {
    "tfl": ("s3-eu-west-1.amazonaws.com", r"/jamcams\.tfl\.gov\.uk/[A-Za-z0-9_.-]+\.jpg"),
    "hongkong": ("tdcctv.data.one.gov.hk", r"/[A-Za-z0-9_-]+\.JPG"),
    "fintraffic": ("weathercam.digitraffic.fi", r"/C[0-9]+\.jpg"),
}


def valid_snapshot(provider: CameraProviderId, url: str) -> bool:
    """Exact HTTPS host and path policy also rejects credentials, queries and ports."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    host, pattern = IMAGE_PATHS[provider]
    return (
        parts.scheme == "https"
        and parts.netloc == host
        and not parts.query
        and not parts.fragment
        and re.fullmatch(pattern, parts.path) is not None
    )


def _camera(
    provider: CameraProviderId, key: Any, title: Any, lat: Any, lon: Any, image: Any
) -> Camera | None:
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", key):
        return None
    if not isinstance(image, str) or not valid_snapshot(provider, image):
        return None
    try:
        latitude, longitude = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        return None
    if provider == "hongkong" and not (22.1 <= latitude <= 22.6 and 113.8 <= longitude <= 114.5):
        return None
    label = str(title or NAMES[provider]).strip()[:240]
    return Camera(
        f"{provider}:{key}",
        provider,
        label,
        latitude,
        longitude,
        image,
        SOURCES[provider],
        ATTRIBUTION[provider],
    )


def parse_tfl(payload: bytes) -> tuple[Camera, ...]:
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("Invalid TfL catalogue")
    cameras = []
    for item in data[:5000]:
        if not isinstance(item, dict):
            continue
        props = {
            p.get("key"): p.get("value")
            for p in item.get("additionalProperties", [])
            if isinstance(p, dict)
        }
        if props.get("available") == "false":
            continue
        camera = _camera(
            "tfl",
            item.get("id"),
            item.get("commonName"),
            item.get("lat"),
            item.get("lon"),
            props.get("imageUrl"),
        )
        if camera:
            cameras.append(camera)
    return _unique(cameras)


def parse_hongkong(payload: bytes) -> tuple[Camera, ...]:
    cameras = []
    for item in fromstring(payload).findall("image")[:5000]:
        camera = _camera(
            "hongkong",
            item.findtext("key"),
            item.findtext("description"),
            item.findtext("latitude"),
            item.findtext("longitude"),
            item.findtext("url"),
        )
        if camera:
            cameras.append(camera)
    return _unique(cameras)


def parse_fintraffic(payload: bytes) -> tuple[Camera, ...]:
    data = json.loads(payload)
    if not isinstance(data, dict) or not isinstance(data.get("features"), list):
        raise ValueError("Invalid Fintraffic catalogue")
    cameras = []
    for item in data["features"][:5000]:
        if not isinstance(item, dict):
            continue
        props, geometry = item.get("properties") or {}, item.get("geometry") or {}
        coords = geometry.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        if props.get("collectionStatus") != "GATHERING":
            continue
        # The simplified index has null legacy states. Explicit repair/fault states
        # are excluded even when the station still says it is gathering.
        if props.get("state") not in (None, "OK", "OK_FAULT_DOUBT_CANCELLED"):
            continue
        preset = next(
            (
                p
                for p in props.get("presets", [])
                if isinstance(p, dict) and p.get("inCollection") is True
            ),
            None,
        )
        if not preset:
            continue
        camera = _camera(
            "fintraffic",
            props.get("id"),
            props.get("name"),
            coords[1],
            coords[0],
            f"https://weathercam.digitraffic.fi/{preset.get('id')}.jpg",
        )
        if camera:
            cameras.append(camera)
    return _unique(cameras)


def _unique(cameras: list[Camera]) -> tuple[Camera, ...]:
    return tuple({camera.id: camera for camera in cameras}.values())[:1500]


class OfficialCameraSource:
    def __init__(self, provider: CameraProviderId, http: FeedHttpClient) -> None:
        self.id = provider
        self.name = NAMES[provider]
        self._http = http

    async def fetch(self) -> tuple[Camera, ...]:
        try:
            # Unconditional requests avoid 304 coupling with this service's own TTL cache.
            payload = await self._http.get_bytes(
                ENDPOINTS[self.id], conditional=False, max_redirects=0
            )
            parser = {"tfl": parse_tfl, "hongkong": parse_hongkong, "fintraffic": parse_fintraffic}
            return parser[self.id](payload)
        except (
            FeedFetchError,
            NotModified,
            ParseError,
            DefusedXmlException,
            TypeError,
            AttributeError,
            KeyError,
            RecursionError,
        ) as exc:
            raise ValueError("Camera catalogue temporarily unavailable") from exc
