"""Distributed whole-Earth query sweep, not a simultaneous global flight snapshot."""

import math
from dataclasses import replace

from ase.adapters.feeds.adsb import adsb_spec
from ase.adapters.feeds.adsb_classification import AircraftClassificationCache
from ase.adapters.feeds.adsb_watch import AdsbAreaConnector, WatchArea
from ase.adapters.feeds.http import FeedHttpClient
from ase.application.ports import Clock
from ase.domain.events import Event, freeze_attributes

SPEC = replace(
    adsb_spec(
        "adsb_global",
        "Worldwide sampled sweep (adsb.lol)",
        "https://api.adsb.lol/v2/point",
        seconds=120,
    ),
    flags=frozenset({"crowd_sourced", "global_sweep", "sampled"}),
    licence_note=(
        "ODbL; volunteer receiver coverage. Bounded rotating sweep, "
        "not a simultaneous worldwide snapshot."
    ),
)
CELLS_PER_POLL = 24


def global_areas() -> tuple[WatchArea, ...]:
    """Five-degree latitude bands, longitude spacing contracted towards the poles.

    Each cell's conservative corner distance is below the provider's 250nm radius.
    A coprime permutation distributes consecutive queries across the planet.
    """
    areas = []
    for band in range(36):
        lat = -87.5 + band * 5
        nearer_equator = max(0.0, abs(lat) - 2.5)
        columns = max(1, math.ceil(72 * math.cos(math.radians(nearer_equator))))
        for column in range(columns):
            lon = -180 + (column + 0.5) * 360 / columns
            areas.append(
                WatchArea(f"global_{band}_{column}", "Worldwide sweep cell", lat, lon, 250)
            )
    stride = round(len(areas) * 0.61803398875)
    while math.gcd(stride, len(areas)) != 1:
        stride += 1
    return tuple(areas[(i * stride) % len(areas)] for i in range(len(areas)))


class AdsbGlobalConnector(AdsbAreaConnector):
    spec = SPEC

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        *,
        classifications: AircraftClassificationCache | None = None,
    ) -> None:
        super().__init__(
            http,
            clock,
            global_areas(),
            classifications=classifications,
            max_areas_per_poll=CELLS_PER_POLL,
            request_interval=1.0,
        )
        self._attempted_total = 0

    @property
    def coverage_warning(self) -> str:
        return (
            f"Sampled worldwide sweep: {self._attempted_total % len(self.areas)}/{len(self.areas)} "
            "cells attempted in cycle "
            f"{self._attempted_total // len(self.areas) + 1}. "
            f"At most {CELLS_PER_POLL} queries per poll; "
            "aircraft expire after 10 minutes, so this is not simultaneous global coverage."
        )

    async def fetch(self) -> list[Event]:
        before = self._start_area
        try:
            events = await super().fetch()
        finally:
            self._attempted_total += (self._start_area - before) % len(self.areas)
        return [
            event.with_changes(
                attributes=freeze_attributes(
                    {
                        **event.attributes,
                        "coverage_kind": "rotating_global_sweep",
                        "sweep_cells_total": len(self.areas),
                        "query_radius_nm": 250,
                        "simultaneous_global_coverage": False,
                    }
                )
            )
            for event in events
        ]
