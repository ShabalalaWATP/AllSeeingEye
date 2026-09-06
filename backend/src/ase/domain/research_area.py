"""Canonical collection areas and exact rectangle capability checks.

Geometry follows the saved-map upload bounds (5 MiB, 100,000 vertices and one
million topology checks). A bounding envelope is never substituted for a polygon.
"""

import json
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from ase.domain.map_geometry import CanonicalMapGeometry, parse_map_geometry
from ase.domain.map_views import MapCamera, MapViewState


@dataclass(frozen=True, slots=True)
class ResearchArea:
    geometry: CanonicalMapGeometry

    def __post_init__(self) -> None:
        if not isinstance(self.geometry, CanonicalMapGeometry):
            raise ValueError("Research area requires canonical geometry")
        # Do not trust manually constructed canonical objects or their cached counters/hash.
        if parse_map_geometry(self.geometry.canonical_json) != self.geometry:
            raise ValueError("Research area canonical geometry is inconsistent")
        MapViewState(MapCamera(0, 0, 0), aoi=self.geometry)

    @property
    def rectangle_bounds(self) -> tuple[float, float, float, float] | None:
        """Only a single, hole-free, four-corner axis-aligned rectangle is eligible.

        Winding and starting corner are immaterial. Nonrectangular areas, holes,
        split/wrapped multipolygons and redundant vertices require another capability.
        """
        geometry = self.geometry.to_collection()["features"][0]["geometry"]
        polygons = (
            [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        )
        if len(polygons) != 1 or len(polygons[0]) != 1:
            return None
        ring = polygons[0][0]
        if len(ring) != 5:
            return None
        xs, ys = {point[0] for point in ring}, {point[1] for point in ring}
        if len(xs) != 2 or len(ys) != 2:
            return None
        if any((a[0] == b[0]) == (a[1] == b[1]) for a, b in pairwise(ring)):
            return None
        west, east = sorted(xs)
        south, north = sorted(ys)
        return float(west), float(south), float(east), float(north)


def area_to_dict(area: ResearchArea | None) -> dict[str, Any] | None:
    """The hash describes exactly the canonical geometry retained in this receipt."""
    if area is None:
        return None
    return {"geometry": area.geometry.to_collection(), "sha256": area.geometry.sha256}


def area_from_dict(value: Any) -> ResearchArea | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"geometry", "sha256"}:
        raise ValueError("Invalid frozen research area")
    try:
        text = json.dumps(value["geometry"], ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid frozen research area geometry") from exc
    geometry = parse_map_geometry(text)
    if value["sha256"] != geometry.sha256:
        raise ValueError("Frozen research area hash does not match its geometry")
    return ResearchArea(geometry)
