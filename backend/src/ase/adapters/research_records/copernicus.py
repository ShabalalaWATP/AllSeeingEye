"""Single-page public STAC metadata search. Asset links are never followed or returned."""

import asyncio
import math
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.footprints import Footprint, FootprintCollection, FootprintQuery, Polygon

BASE = "https://stac.dataspace.copernicus.eu/v1"
COLLECTION = "sentinel-2-l2a"
MAX_FEATURES = 20
MAX_VERTICES = 100_000
LICENCE_URL = "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice"
LIMITATIONS = (
    "Copernicus Sentinel-2 L2A catalogue footprints, not downloaded imagery or verified events. "
    "One page, at most 20 features; additional results are not followed. Footprints show "
    "catalogue scene coverage, not usable or cloud-free coverage of the selected area. "
    "Cloud percentage describes the scene and may not describe the selected area. "
    "Capture time is distinct from processing/publication time. No imagery, thumbnails or "
    "assets are fetched. Copernicus Sentinel data legal notice applies; retain attribution."
)


def _polygons(raw: Any, remaining: int) -> tuple[tuple[Polygon, ...], int]:
    if not isinstance(raw, dict) or raw.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Expected polygon footprint")
    coordinates = raw.get("coordinates")
    polygons = [coordinates] if raw["type"] == "Polygon" else coordinates
    if not isinstance(polygons, list) or not 1 <= len(polygons) <= 1000:
        raise ValueError("Invalid polygon count")
    result, count = [], 0
    for polygon in polygons:
        if not isinstance(polygon, list) or not 1 <= len(polygon) <= 1000:
            raise ValueError("Invalid polygon rings")
        rings = []
        for ring in polygon:
            if not isinstance(ring, list) or not 4 <= len(ring) <= remaining - count:
                raise ValueError("Footprint vertex limit exceeded")
            points = []
            for point in ring:
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or any(
                        type(value) not in (int, float) or not math.isfinite(value)
                        for value in point
                    )
                ):
                    raise ValueError("Invalid WGS84 coordinate")
                lon, lat = float(point[0]), float(point[1])
                if not -180 <= lon <= 180 or not -90 <= lat <= 90:
                    raise ValueError("Coordinate outside WGS84 bounds")
                points.append((lon, lat))
            if points[0] != points[-1]:
                raise ValueError("Unclosed polygon ring")
            count += len(points)
            rings.append(tuple(points))
        result.append(tuple(rings))
    return tuple(result), count


class CopernicusFootprintProvider:
    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    async def search(self, query: FootprintQuery) -> FootprintCollection:
        params = {
            "collections": COLLECTION,
            "bbox": ",".join(str(value) for value in query.bbox),
            "datetime": "/".join(
                value.astimezone(UTC).isoformat().replace("+00:00", "Z")
                for value in (query.since, query.until)
            ),
            "limit": str(MAX_FEATURES),
            "fields": "-assets",
            "sortby": "-properties.datetime",
        }
        try:
            async with asyncio.timeout(20):
                data = await self._http.get_json(
                    BASE + "/search?" + urlencode(params), conditional=False, max_redirects=0
                )
            return self._parse(data, query)
        except (
            FeedFetchError,
            NotModified,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            OverflowError,
            RecursionError,
        ):
            return FootprintCollection(
                (),
                "unavailable",
                False,
                "The catalogue was unavailable or returned unsupported metadata. "
                "No coverage was established. " + LIMITATIONS,
                self._clock.now(),
            )

    def _parse(self, data: Any, query: FootprintQuery) -> FootprintCollection:
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            raise ValueError("Expected STAC FeatureCollection")
        rows = data.get("features")
        if not isinstance(rows, list) or len(rows) > MAX_FEATURES:
            raise ValueError("Unexpected feature count")
        features, seen, vertices = [], set(), 0
        for row in rows:
            if (
                not isinstance(row, dict)
                or row.get("type") != "Feature"
                or row.get("collection") != COLLECTION
            ):
                raise ValueError("Unexpected feature or collection")
            identity = row.get("id")
            if (
                not isinstance(identity, str)
                or not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", identity)
                or identity in seen
            ):
                raise ValueError("Invalid or duplicate STAC identity")
            seen.add(identity)
            properties = row.get("properties")
            if not isinstance(properties, dict) or not isinstance(properties.get("datetime"), str):
                raise ValueError("Missing acquisition time")
            captured = datetime.fromisoformat(properties["datetime"].replace("Z", "+00:00"))
            if captured.utcoffset() is None or not query.since <= captured <= query.until:
                raise ValueError("Capture time outside query")
            if captured == query.until:
                continue  # STAC interval ends can be inclusive; application end is exclusive.
            cloud = properties.get("eo:cloud_cover")
            if cloud is not None and (
                type(cloud) not in (int, float) or not math.isfinite(cloud) or not 0 <= cloud <= 100
            ):
                raise ValueError("Invalid scene cloud percentage")
            polygons, count = _polygons(row.get("geometry"), MAX_VERTICES - vertices)
            vertices += count
            # Extent check does not assert an exact polygon intersection or usable coverage.
            positions = [point for polygon in polygons for ring in polygon for point in ring]
            west, south, east, north = query.bbox
            if (
                max(point[0] for point in positions) < west
                or min(point[0] for point in positions) > east
                or max(point[1] for point in positions) < south
                or min(point[1] for point in positions) > north
            ):
                raise ValueError("Footprint outside requested extent")
            features.append(
                Footprint(
                    identity,
                    polygons,
                    COLLECTION,
                    captured.astimezone(UTC),
                    float(cloud) if cloud is not None else None,
                    f"{BASE}/collections/{COLLECTION}/items/{identity}",
                    "Copernicus Sentinel data legal notice",
                    LICENCE_URL,
                )
            )
        links = data.get("links", [])
        if not isinstance(links, list) or len(links) > 100:
            raise ValueError("Invalid catalogue links")
        truncated = any(isinstance(link, dict) and link.get("rel") == "next" for link in links)
        return FootprintCollection(
            tuple(features),
            "completed" if features else "empty",
            truncated,
            LIMITATIONS,
            self._clock.now(),
        )
