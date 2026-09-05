"""Country lookup from the packaged Natural Earth 1:110m polygons (public domain).

A bounding-box pass narrows the candidates, then ray casting decides. The scale is
coarse near coasts and small islands, which is acceptable for attributing events;
the resolver returns None rather than guessing when no polygon contains the point.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from functools import lru_cache
from importlib.resources import files
from typing import Any

from ase.domain.countries import Country
from ase.domain.geometry import Bounds, Ring, bounds_contain, point_in_polygon, ring_bounds

RESOURCE = "countries_110m.json"


@lru_cache(maxsize=1)
def load_records() -> tuple[Mapping[str, Any], ...]:
    text = files("ase.resources").joinpath(RESOURCE).read_text("utf-8")
    data = json.loads(text)
    return tuple(data["countries"])


class CountryIndex:
    def __init__(self, records: Iterable[Mapping[str, Any]]) -> None:
        self._polygons: list[tuple[Bounds, list[Ring], str]] = []
        self._countries: dict[str, Country] = {}
        for record in records:
            self._add(record)

    @classmethod
    def from_resource(cls) -> CountryIndex:
        return cls(load_records())

    def _add(self, record: Mapping[str, Any]) -> None:
        iso2 = str(record["iso2"]).upper()
        boxes: list[Bounds] = []
        for rings in record.get("polygons", []):
            if not rings or len(rings[0]) < 3:
                continue
            bounds = ring_bounds(rings[0])
            boxes.append(bounds)
            self._polygons.append((bounds, rings, iso2))
        if not boxes:
            return
        largest = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        self._countries[iso2] = Country(
            iso2=iso2,
            iso3=str(record.get("iso3") or "").upper(),
            name=str(record.get("name") or iso2),
            bounds=(
                min(b[0] for b in boxes),
                min(b[1] for b in boxes),
                max(b[2] for b in boxes),
                max(b[3] for b in boxes),
            ),
            centroid=((largest[0] + largest[2]) / 2, (largest[1] + largest[3]) / 2),
        )

    def resolve(self, lon: float, lat: float) -> str | None:
        for bounds, rings, iso2 in self._polygons:
            if bounds_contain(bounds, lon, lat) and point_in_polygon(lon, lat, rings):
                return iso2
        return None

    def get(self, iso2: str) -> Country | None:
        return self._countries.get(iso2.upper())

    def countries(self) -> list[Country]:
        return sorted(self._countries.values(), key=lambda country: country.name)

    def __len__(self) -> int:
        return len(self._countries)
