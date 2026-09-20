"""Exact point membership for bounded operational areas, never their envelopes."""

import json
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise

from ase.domain.events import Event, GeoConfidence
from ase.domain.evidence_geometry import LocationRole
from ase.domain.map_topology import Position, Ring
from ase.domain.research_area import ResearchArea


@dataclass(frozen=True, slots=True)
class _Polygon:
    rings: tuple[Ring, ...]
    bounds: tuple[float, float, float, float]


@lru_cache(maxsize=128)
def _polygons(text: str) -> tuple[_Polygon, ...]:
    geometry = json.loads(text)["features"][0]["geometry"]
    polygons = (
        [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    )
    rings = tuple(
        tuple(tuple((float(x), float(y)) for x, y in ring) for ring in polygon)
        for polygon in polygons
    )
    return tuple(
        _Polygon(
            polygon,
            (
                min(x for x, _ in polygon[0]),
                min(y for _, y in polygon[0]),
                max(x for x, _ in polygon[0]),
                max(y for _, y in polygon[0]),
            ),
        )
        for polygon in rings
    )


def _ring_location(point: Position, ring: Ring) -> int:
    """Return outside (0), inside (1) or on the exact boundary (2)."""
    x, y = point
    inside = False
    for a, b in pairwise(ring):
        cross = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
        if (
            cross == 0
            and min(a[0], b[0]) <= x <= max(a[0], b[0])
            and min(a[1], b[1]) <= y <= max(a[1], b[1])
        ):
            return 2
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return int(inside)


def area_contains_event(area: ResearchArea, event: Event) -> bool:
    """Only incident/site points with exact location quality establish membership.

    Canonical polygons are already validated and split at the antimeridian.
    Outer and hole boundaries count; hole interiors do not. Mirrors research
    collection's strict point policy without importing a geospatial adapter.
    """
    point = event.point
    if point is None or event.geo_confidence is not GeoConfidence.EXACT:
        return False
    if event.source_id == "nasa_eonet" and (
        event.geometry is None
        or event.geometry.source_id != event.source_id
        or event.geometry.location_role is not LocationRole.INCIDENT
    ):
        return False
    if event.geometry is not None:
        geometry = event.geometry.to_geometry()
        if (
            event.geometry.location_role not in {LocationRole.INCIDENT, LocationRole.PROJECT_SITE}
            or geometry["type"] != "Point"
            or geometry["coordinates"] != [point.lon, point.lat]
        ):
            return False
    for polygon in _polygons(area.geometry.canonical_json):
        west, south, east, north = polygon.bounds
        if not west <= point.lon <= east or not south <= point.lat <= north:
            continue
        outer = _ring_location((point.lon, point.lat), polygon.rings[0])
        if outer and not any(
            _ring_location((point.lon, point.lat), hole) == 1 for hole in polygon.rings[1:]
        ):
            return True
    return False
