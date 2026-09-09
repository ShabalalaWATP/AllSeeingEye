"""Cumulative sensor caps shared by NASA's public and keyed delivery methods."""

from collections.abc import Mapping
from math import floor

from ase.domain.events import Event

MAX_RETAINED_PER_SENSOR = 10_000
SENSOR_SOURCES = (
    ("firms_viirs_noaa20", "firms_public_noaa20"),
    ("firms_viirs_noaa21", "firms_public_noaa21"),
)


def firms_evictions(events: Mapping[str, Event], by_source: Mapping[str, set[str]]) -> list[str]:
    """Keep cell representatives, then newest acquisitions; never select other feeds."""
    evicted: list[str] = []
    for sources in SENSOR_SOURCES:
        if sum(len(by_source.get(source, ())) for source in sources) <= MAX_RETAINED_PER_SENSOR:
            continue
        ids = set().union(*(by_source.get(source, set()) for source in sources))
        if len(ids) <= MAX_RETAINED_PER_SENSOR:
            continue
        ordered = sorted(
            ids,
            key=lambda identifier: (
                events[identifier].published_at or events[identifier].observed_at,
                events[identifier].observed_at,
                identifier,
            ),
            reverse=True,
        )
        cells: dict[tuple[int, int], str] = {}
        for identifier in ordered:
            point = events[identifier].point
            if point is not None:
                cell = (
                    floor(((point.lon + 180) % 360) / 5),
                    min(35, floor((point.lat + 90) / 5)),
                )
                cells.setdefault(cell, identifier)
        keep = set(cells.values())
        for identifier in ordered:
            if len(keep) >= MAX_RETAINED_PER_SENSOR:
                break
            keep.add(identifier)
        evicted.extend(identifier for identifier in ordered if identifier not in keep)
    return evicted
