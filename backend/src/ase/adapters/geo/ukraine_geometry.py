"""Shapely to plain rounded coordinate lists, so snapshots stay small and JSON-only."""

from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

DECIMALS = 4


def _ring(coords: Iterable[tuple[float, ...]]) -> list[list[float]]:
    return [
        [round(float(point[0]), DECIMALS), round(float(point[1]), DECIMALS)] for point in coords
    ]


def polygon_lists(geometry: BaseGeometry) -> list[list[list[list[float]]]]:
    """Every polygon as [exterior, *holes]; other geometry types contribute nothing."""
    parts: list[Polygon]
    if isinstance(geometry, Polygon):
        parts = [geometry]
    elif isinstance(geometry, MultiPolygon):
        parts = list(geometry.geoms)
    else:
        parts = [part for part in getattr(geometry, "geoms", ()) if isinstance(part, Polygon)]
    return [
        [_ring(part.exterior.coords), *[_ring(hole.coords) for hole in part.interiors]]
        for part in parts
        if not part.is_empty
    ]
