"""A country as the resolver knows it: codes, name, extent and a point to fly to."""

from __future__ import annotations

from dataclasses import dataclass

Bounds = tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat


@dataclass(frozen=True, slots=True)
class Country:
    iso2: str
    iso3: str
    name: str
    bounds: Bounds
    centroid: tuple[float, float]  # (lon, lat) of the largest polygon's box
