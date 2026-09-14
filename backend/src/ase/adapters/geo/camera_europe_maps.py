"""Official European camera maps published as KML or WFS GeoJSON. See docs/CAMERA_EUROPE.md.

Luxembourg's CITA motorway cameras (CC0 on data.public.lu), the city of Madrid's traffic
cameras (Informo, Madrid open data) and the Lyon metropolitan Criter web cameras.
"""

import json
import re
from html import unescape
from typing import Any

from defusedxml.ElementTree import fromstring

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_curated import HostPolicy, collect
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

ENDPOINTS = {
    "luxembourg": "https://www.cita.lu/kml/cameras.kml",
    "madrid": "https://informo.madrid.es/informo/tmadrid/CCTV.kml",
    "lyon": (
        "https://data.grandlyon.com/geoserver/metropole-de-lyon/ows?SERVICE=WFS&VERSION=2.0.0"
        "&request=GetFeature&typename=metropole-de-lyon:pvo_patrimoine_voirie.pvocameracriter"
        "&outputFormat=application/json&SRSNAME=EPSG:4326"
    ),
}
NAMES = {
    "luxembourg": "CITA (Luxembourg)",
    "madrid": "Ayuntamiento de Madrid (Informo)",
    "lyon": "Metropole de Lyon (Criter)",
}
PAGES = {
    "luxembourg": "https://www.cita.lu/",
    "madrid": "https://informo.madrid.es/",
    "lyon": "https://data.grandlyon.com/",
}
MEDIA_HOSTS = frozenset({"www.cita.lu", "informo.madrid.es", "download.data.grandlyon.com"})
POLICY = HostPolicy(MEDIA_HOSTS, frozenset(), MEDIA_HOSTS, NAMES, PAGES)
MADRID_IMAGE = re.compile(r"src=(https://informo\.madrid\.es/cameras/Camara\d{1,8}\.jpg)")


def _local(tag: Any) -> str:
    return str(tag).rsplit("}", 1)[-1]


def _child(node: Any, name: str) -> Any:
    return next((child for child in node.iter() if _local(child.tag) == name), None)


def _placemarks(payload: bytes) -> list[Any]:
    try:
        root = fromstring(payload)
    except Exception as exc:
        raise ValueError("Invalid camera KML") from exc
    return [node for node in root.iter() if _local(node.tag) == "Placemark"][:5000]


def _point(node: Any) -> tuple[str, str] | None:
    coordinates = _child(node, "coordinates")
    parts = (coordinates.text or "").strip().split(",") if coordinates is not None else []
    return (parts[1], parts[0]) if len(parts) >= 2 else None


def parse_luxembourg(payload: bytes) -> list[dict[str, Any]]:
    rows = []
    for node in _placemarks(payload):
        match = re.fullmatch(r"camera_(\d{1,6})", str(node.get("id")))
        point, name = _point(node), _child(node, "name")
        if not match or point is None:
            continue
        rows.append(
            {
                "id": match[1],
                "name": name.text if name is not None else None,
                "lat": point[0],
                "lng": point[1],
                "feed_url": f"https://www.cita.lu/info_trafic/cameras/images/cccam_{match[1]}.jpg",
            }
        )
    return rows


def parse_madrid(payload: bytes) -> list[dict[str, Any]]:
    rows = []
    for node in _placemarks(payload):
        values = {
            str(data.get("name")): (_child(data, "Value").text or "").strip()
            for data in node.iter()
            if _local(data.tag) == "Data" and _child(data, "Value") is not None
        }
        description = _child(node, "description")
        image = (
            MADRID_IMAGE.search(unescape(description.text or ""))
            if description is not None
            else None
        )
        point = _point(node)
        if point is None or image is None:
            continue
        rows.append(
            {
                "id": values.get("Numero"),
                "name": values.get("Nombre"),
                "lat": point[0],
                "lng": point[1],
                "feed_url": image[1],
            }
        )
    return rows


def parse_lyon(payload: bytes) -> list[dict[str, Any]]:
    data = json.loads(payload)
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list):
        raise ValueError("Invalid Lyon camera collection")
    rows = []
    for feature in features[:5000]:
        if not isinstance(feature, dict):
            continue
        raw_props, raw_geometry = feature.get("properties"), feature.get("geometry")
        props: dict[str, Any] = raw_props if isinstance(raw_props, dict) else {}
        geometry: dict[str, Any] = raw_geometry if isinstance(raw_geometry, dict) else {}
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        label = " - ".join(str(v) for v in (props.get("nom"), props.get("libellelong")) if v)
        rows.append(
            {
                "id": props.get("identifiant"),
                "name": label or None,
                "lat": coordinates[1],
                "lng": coordinates[0],
                "feed_url": props.get("url"),
            }
        )
    return rows


PARSERS = {"luxembourg": parse_luxembourg, "madrid": parse_madrid, "lyon": parse_lyon}


def parse(provider: str, payload: bytes) -> tuple[Camera, ...]:
    cameras = collect(POLICY, provider, PARSERS[provider](payload), approximate=False)
    if not cameras:
        raise ValueError(f"{NAMES[provider]} returned no usable public cameras")
    return cameras


class EuropeMapSource:
    def __init__(self, provider: str, http: FeedHttpClient) -> None:
        self.id, self.name, self.http = provider, NAMES[provider], http

    async def fetch(self) -> tuple[Camera, ...]:
        payload = await self.http.get_bytes(
            ENDPOINTS[self.id], conditional=False, max_redirects=0, accept="*/*"
        )
        return parse(self.id, payload)


def build_sources(http: FeedHttpClient) -> tuple[CameraSource, ...]:
    return tuple(EuropeMapSource(provider, http) for provider in ENDPOINTS)
