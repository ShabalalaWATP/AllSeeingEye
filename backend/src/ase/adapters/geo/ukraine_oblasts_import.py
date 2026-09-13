"""Oblast outlines from geoBoundaries (ODbL), simplified once into a small packaged file."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from shapely.geometry import shape

from ase.adapters.geo.bounded_download import DEFAULT_CONTACT, download_to, user_agent
from ase.adapters.geo.ukraine_geometry import polygon_lists
from ase.domain.ukraine.control import MAX_OUTLINE_VERTICES, MAX_OUTLINES

API_URL = "https://www.geoboundaries.org/api/current/gbOpen/UKR/ADM1/"
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
TOLERANCE_DEGREES = 0.01
ATTRIBUTION = "geoBoundaries (ODbL), OpenStreetMap contributors via Wambacher"


def parse_outlines(collection: dict[str, Any]) -> list[dict[str, Any]]:
    """Name, ISO code and simplified rings for each oblast-level feature."""
    features = collection.get("features")
    if not isinstance(features, list) or not 0 < len(features) <= MAX_OUTLINES:
        raise ValueError("Unexpected geoBoundaries feature count")
    outlines: list[dict[str, Any]] = []
    for feature in features:
        properties = feature.get("properties") or {}
        geometry = shape(feature["geometry"]).simplify(TOLERANCE_DEGREES, preserve_topology=True)
        outlines.append(
            {
                "name": str(properties.get("shapeName") or "")[:80],
                "iso": str(properties.get("shapeISO") or "")[:8],
                "polygons": polygon_lists(geometry),
            }
        )
    vertices = sum(
        len(ring) for item in outlines for polygon in item["polygons"] for ring in polygon
    )
    if vertices > MAX_OUTLINE_VERTICES:
        raise ValueError("Simplified outlines still exceed the vertex bound")
    return sorted(outlines, key=lambda item: item["name"])


def import_ukraine_oblasts(destination: str, contact: str = DEFAULT_CONTACT) -> int:
    with httpx.Client(timeout=120, headers={"User-Agent": user_agent(contact)}) as client:
        meta = client.get(API_URL, follow_redirects=True)
        meta.raise_for_status()
        url = str(meta.json().get("simplifiedGeometryGeoJSON") or "")
        if not url.startswith("https://"):
            raise ValueError("geoBoundaries did not return a download link")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "oblasts.geojson"
            download_to(client, url, path, MAX_DOWNLOAD_BYTES)
            outlines = parse_outlines(json.loads(path.read_text(encoding="utf-8")))
    payload = {
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_url": API_URL,
        "attribution": ATTRIBUTION,
        "licence": "ODbL 1.0",
        "outlines": outlines,
    }
    Path(destination).write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return len(outlines)
