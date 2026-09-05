"""Point-in-polygon on longitude and latitude, enough to attribute an event to a country."""

from __future__ import annotations

from collections.abc import Sequence

Coordinate = Sequence[float]  # (lon, lat)
Ring = Sequence[Coordinate]
Bounds = tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat


def ring_bounds(ring: Ring) -> Bounds:
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return (min(lons), min(lats), max(lons), max(lats))


def bounds_contain(bounds: Bounds, lon: float, lat: float) -> bool:
    return bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]


def point_in_ring(lon: float, lat: float, ring: Ring) -> bool:
    """Even-odd ray casting; points on an edge count as inside often enough for our use."""
    inside = False
    count = len(ring)
    if count < 3:
        return False
    j = count - 1
    for i in range(count):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            crossing = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < crossing:
                inside = not inside
        j = i
    return inside


def point_in_polygon(lon: float, lat: float, rings: Sequence[Ring]) -> bool:
    """The first ring is the outer boundary; any further rings are holes."""
    if not rings or not point_in_ring(lon, lat, rings[0]):
        return False
    return not any(point_in_ring(lon, lat, hole) for hole in rings[1:])
