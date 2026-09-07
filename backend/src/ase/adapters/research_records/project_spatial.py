"""Bounded planar intersections of retained source polygons and exact research areas."""

from itertools import pairwise
from typing import Any

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from ase.domain.evidence_geometry import EvidenceGeometry
from ase.domain.research_area import ResearchArea

MAX_QUERY_VERTICES = 200_000


def _polygon(raw: dict[str, Any]) -> BaseGeometry:
    if raw["type"] not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Project area search requires polygon geometry")
    polygons = [raw["coordinates"]] if raw["type"] == "Polygon" else raw["coordinates"]
    for polygon in polygons:
        for ring in polygon:
            if any(abs(a[0] - b[0]) > 180 for a, b in pairwise(ring)):
                raise ValueError("Project geometry crosses the seam without explicit splitting")
    result = shape(raw)
    if result.is_empty or not result.is_valid:
        raise ValueError("Project area search requires valid nonempty geometry")
    return result


class ProjectSpatialFilter:
    def __init__(self, area: ResearchArea) -> None:
        self._vertices = area.geometry.vertices
        feature = area.geometry.to_collection()["features"][0]
        self._area = _polygon(feature["geometry"])

    def intersects(self, geometry: EvidenceGeometry | None) -> bool:
        if geometry is None:
            return False
        self._vertices += geometry.vertices
        if self._vertices > MAX_QUERY_VERTICES:
            raise ValueError("Project area search exceeds its total geometry work limit")
        # No buffering, repair, simplification or envelope substitution. Boundary
        # contact counts as intersection, not proof of activity inside the area.
        return bool(self._area.intersects(_polygon(geometry.to_geometry())))
