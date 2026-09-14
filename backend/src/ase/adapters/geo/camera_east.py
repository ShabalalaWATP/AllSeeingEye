"""Estonia's official camera index plus curated Baltic, Russian, Israeli, Iraqi, Iranian and
Chinese public streams.

The Estonian Transport Administration publishes camera positions and current image links as a
public DATEX II location publication without a key. Tallinn's junction cameras are a public
city page whose positions were geocoded once from the junction names and are therefore
approximate. Every other provider here is a curated YouTube embed or operator page; a listed
stream is not an assertion that its owner is broadcasting now.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import fromstring

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_curated import HostPolicy, collect, curated_rows
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

ENDPOINT = "https://tarktee.transpordiamet.ee/api/v1/datex/v3.6/roadCameraLocations"
MEDIA_HOSTS = frozenset({"tarktee.transpordiamet.ee", "ristmikud.tallinn.ee"})
FRAME_HOSTS = frozenset({"www.youtube.com"})
EXTERNAL_HOSTS = MEDIA_HOSTS | FRAME_HOSTS | {"tarktee.mnt.ee", "www.skylinewebcams.com"}
NAMES = {
    "estonia": "Transpordiamet Tark Tee (Estonia)",
    "tallinn": "Tallinn junction cameras",
    "baltic-live": "Baltic public streams",
    "russia-live": "Russia public streams",
    "israel-live": "Israel public streams",
    "iraq-iran-live": "Iraq and Iran public streams",
    "china-live": "China public streams",
}
PAGES = {"estonia": "https://tarktee.mnt.ee/", "tallinn": "https://ristmikud.tallinn.ee/"}
CURATED = tuple(name for name in NAMES if name != "estonia")
ESTONIA_BOUNDS = (57.4, 59.9, 21.5, 28.3)
POLICY = HostPolicy(MEDIA_HOSTS, FRAME_HOSTS, EXTERNAL_HOSTS, NAMES, PAGES)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: Any, name: str) -> str | None:
    for child in node.iter():
        if _local(child.tag) == name and child.text and child.text.strip():
            return str(child.text.strip())
    return None


def _image_link(node: Any) -> str | None:
    for link in node.iter():
        if _local(link.tag) != "urlLink":
            continue
        if _text(link, "urlLinkType") == "image":
            return _text(link, "urlLinkAddress")
    return None


def parse_estonia(payload: bytes) -> tuple[Camera, ...]:
    """DATEX II predefined locations: one point, an Estonian name and a current image link."""
    try:
        root = fromstring(payload)
    except Exception as exc:
        raise ValueError("Invalid Estonian camera catalogue") from exc
    rows: list[dict[str, Any]] = []
    for node in root.iter():
        if _local(node.tag) != "predefinedLocationReference":
            continue
        if len(rows) >= 5000:
            break
        try:
            lat = float(_text(node, "latitude") or "nan")
            lon = float(_text(node, "longitude") or "nan")
        except ValueError:
            continue
        south, north, west, east = ESTONIA_BOUNDS
        if not (south <= lat <= north and west <= lon <= east):
            continue
        rows.append(
            {
                "id": node.get("id"),
                "name": _text(node, "value"),
                "lat": lat,
                "lng": lon,
                "feed_url": _image_link(node),
                "source": "Transpordiamet (Estonian Transport Administration)",
            }
        )
    cameras = collect(POLICY, "estonia", rows, approximate=False)
    if not cameras:
        raise ValueError("Estonian camera catalogue held no supported cameras")
    return cameras


@dataclass
class EstoniaCameraSource:
    http: FeedHttpClient
    id: str = "estonia"
    name: str = NAMES["estonia"]

    async def fetch(self) -> tuple[Camera, ...]:
        # The server frames its JSON variant with two Transfer-Encoding headers, which the
        # HTTP client rightly refuses; asking for XML returns a plain Content-Length body.
        payload = await self.http.get_bytes(
            ENDPOINT, conditional=False, max_redirects=0, accept="application/xml"
        )
        return parse_estonia(payload)


@dataclass
class CuratedEastSource:
    id: str
    name: str
    cameras: tuple[Camera, ...]

    async def fetch(self) -> tuple[Camera, ...]:
        return self.cameras


def load_catalogue() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("camera_east_catalogue.json")
    records = json.loads(path.read_text("utf8"))
    if not isinstance(records, list):
        raise ValueError("Invalid eastern camera catalogue")
    return records


def curated(provider: str, records: list[dict[str, Any]] | None = None) -> tuple[Camera, ...]:
    rows = curated_rows(records if records is not None else load_catalogue(), provider)
    return collect(POLICY, provider, rows, approximate=True)


def build_sources(http: FeedHttpClient) -> tuple[CameraSource, ...]:
    records = load_catalogue()
    sources: list[CameraSource] = [EstoniaCameraSource(http)]
    for provider in CURATED:
        sources.append(CuratedEastSource(provider, NAMES[provider], curated(provider, records)))
    return tuple(sources)
