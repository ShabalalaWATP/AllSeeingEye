"""Resolve a research scope to a geography this application already holds, or to nothing.

No gazetteer, no geocoder and no new download. A drawn outline, a saved map area, the
packaged Natural Earth country outlines and the curated conflict boxes are the only
geographies available, and each carries the limitation that belongs to it. Resolving a
geography is a collection choice about where to look; it never establishes that
anything happened there.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from shapely.geometry import LineString, MultiPolygon, Polygon, shape
from shapely.geometry import Point as ShapePoint
from shapely.ops import unary_union
from shapely.prepared import prep

from ase.adapters.geo.countries import load_records
from ase.domain.research_area import ResearchArea

MAX_COUNTRIES = 8
MAX_PATH_VERTICES = 4_000

DRAWN_LIMITATION = (
    "The outline was drawn by the operator. It is a collection choice, not a boundary of "
    "anything that happened, and records inside it are catalogue entries, not observations."
)
COUNTRY_LIMITATION = (
    "Natural Earth 1:110m country outlines: coarse near coasts, small islands and disputed "
    "boundaries, and they exclude territorial waters, so offshore and near-shore records "
    "under-report. A country outline is a collection choice, not a claim about a location."
)
CONFLICT_LIMITATION = (
    "The curated conflict box is deliberately generous and is not a conflict boundary, a "
    "front line or an area of control. Records inside it are not conflict-related records."
)


@dataclass(frozen=True, slots=True)
class ScopeGeography:
    """One resolved outline, its basis and the limitation that belongs to that basis."""

    basis: str
    label: str
    limitation: str
    digest: str
    bounds: tuple[float, float, float, float]

    def describe(self) -> str:
        return f"{self.label} [{self.basis}]. {self.limitation}"


class ResolvedScope:
    """A prepared outline plus its receipt. Construction validates the topology."""

    def __init__(self, geometry: Polygon | MultiPolygon, scope: ScopeGeography) -> None:
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError("Unsupported scope topology")
        self._prepared = prep(geometry)
        self.scope = scope

    def contains_point(self, lon: float, lat: float) -> bool:
        return bool(self._prepared.covers(ShapePoint(lon, lat)))

    def crosses_path(self, path: list[Any]) -> bool:
        """Exact intersection with a mapped line, never a bounding-envelope substitute."""
        if len(path) < 2 or len(path) > MAX_PATH_VERTICES:
            return False
        try:
            line = LineString([(float(point[0]), float(point[1])) for point in path])
        except (TypeError, ValueError, IndexError):
            return False
        return bool(not line.is_empty and line.is_valid and self._prepared.intersects(line))


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]


def _bounds(geometry: Polygon | MultiPolygon) -> tuple[float, float, float, float]:
    west, south, east, north = geometry.bounds
    return float(west), float(south), float(east), float(north)


def from_area(area: ResearchArea, *, saved: bool = False) -> ResolvedScope:
    geometry = shape(area.geometry.to_collection()["features"][0]["geometry"])
    if not isinstance(geometry, Polygon | MultiPolygon):
        raise ValueError("A research area must be a polygon or multipolygon")
    basis = "saved_map_area" if saved else "drawn_area"
    label = "the saved map area" if saved else "the drawn area"
    return ResolvedScope(
        geometry,
        ScopeGeography(
            basis, label, DRAWN_LIMITATION, area.geometry.sha256[:32], _bounds(geometry)
        ),
    )


def _country_polygons(iso: str) -> list[Polygon]:
    result: list[Polygon] = []
    for record in load_records():
        if str(record["iso2"]).upper() != iso:
            continue
        for rings in record.get("polygons", []):
            if not rings or len(rings[0]) < 4:
                continue
            try:
                polygon = Polygon(rings[0], rings[1:])
            except (TypeError, ValueError):
                continue
            if polygon.is_valid and not polygon.is_empty:
                result.append(polygon)
    return result


def country_name(iso: str) -> str | None:
    return next(
        (
            str(record.get("name") or iso)
            for record in load_records()
            if str(record["iso2"]).upper() == iso.upper()
        ),
        None,
    )


def from_countries(isos: tuple[str, ...]) -> ResolvedScope | None:
    """The union of the packaged outlines, or None when no supplied code is packaged."""
    codes = tuple(dict.fromkeys(value.upper() for value in isos))[:MAX_COUNTRIES]
    polygons = [polygon for iso in codes for polygon in _country_polygons(iso)]
    if not polygons:
        return None
    # Natural Earth parts can touch or overlap, so the union is taken rather than a
    # bare multipolygon, which would fail its own validity check.
    merged = polygons[0] if len(polygons) == 1 else unary_union(polygons)
    if not isinstance(merged, Polygon | MultiPolygon):
        return None
    geometry: Polygon | MultiPolygon = merged
    named = ", ".join(country_name(iso) or iso for iso in codes)
    return ResolvedScope(
        geometry,
        ScopeGeography(
            "country_outline",
            f"the packaged outline of {named}",
            COUNTRY_LIMITATION,
            _digest("country", *codes),
            _bounds(geometry),
        ),
    )


def from_conflict_box(
    conflict_id: str, name: str, box: tuple[float, float, float, float]
) -> ResolvedScope:
    west, south, east, north = box
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Unsupported conflict bounding box")
    geometry = Polygon([(west, south), (east, south), (east, north), (west, north), (west, south)])
    return ResolvedScope(
        geometry,
        ScopeGeography(
            "conflict_box",
            f"the curated collection box for {name}",
            CONFLICT_LIMITATION,
            _digest("conflict", conflict_id),
            _bounds(geometry),
        ),
    )
