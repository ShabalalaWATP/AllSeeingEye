"""Emergency squawks and area traffic from adsb.lol: what the aviation tracker watches for.

The squawk connector asks for 7700 (general emergency), 7600 (radio failure) and 7500
(unlawful interference) each poll. The area connector asks for every aircraft within a
radius of each watched area (docs/04 section 5.3), which is how civil traffic over the
tension areas reaches the globe without any key.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

# Requires Python >=3.12; this standard-library API is supported.
# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from importlib import resources
from typing import Any

from ase.adapters.feeds.adsb import adsb_spec, aircraft_event, records
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import Event, Reliability

SQUAWKS: dict[str, tuple[str, float]] = {
    "7500": ("unlawful interference", 0.95),
    "7700": ("general emergency", 0.8),
    "7600": ("radio failure", 0.6),
}
MAX_RADIUS_NM = 250
RESOURCE = "air_watch.json"

EMERGENCY = adsb_spec(
    "adsb_emergency",
    "Emergency squawks (adsb.lol ADS-B)",
    "https://api.adsb.lol/v2/sqk/7700",
    reliability=Reliability.A,
)
AREAS = adsb_spec(
    "adsb_areas",
    "Traffic over watched areas (adsb.lol ADS-B)",
    "https://api.adsb.lol/v2/point",
    seconds=120,
)


@dataclass(frozen=True, slots=True)
class WatchArea:
    id: str
    name: str
    lat: float
    lon: float
    radius_nm: int

    @property
    def url(self) -> str:
        return f"https://api.adsb.lol/v2/point/{self.lat:g}/{self.lon:g}/{self.radius_nm}"


def _area(raw: dict[str, Any]) -> WatchArea:
    area = WatchArea(
        id=str(raw["id"]),
        name=str(raw.get("name", raw["id"])),
        lat=float(raw["lat"]),
        lon=float(raw["lon"]),
        radius_nm=min(MAX_RADIUS_NM, max(1, int(raw.get("radius_nm", MAX_RADIUS_NM)))),
    )
    if not (-90 <= area.lat <= 90 and -180 <= area.lon <= 180):
        raise ValueError(f"Watch area {area.id} is out of range")
    return area


def load_watch_areas() -> tuple[WatchArea, ...]:
    text = resources.files("ase.resources").joinpath(RESOURCE).read_text(encoding="utf-8")
    return tuple(_area(item) for item in json.loads(text)["areas"])


class AdsbSquawkConnector:
    """Aircraft squawking an emergency code, graded severe; one query per code."""

    spec = EMERGENCY

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        events: list[Event] = []
        seen: set[str] = set()
        for code, (meaning, severity) in SQUAWKS.items():
            try:
                data = await self._http.get_json(
                    f"https://api.adsb.lol/v2/sqk/{code}", conditional=False
                )
            except (FeedFetchError, NotModified):
                continue
            for item in records(data):
                event = aircraft_event(
                    self.spec,
                    item,
                    now,
                    subtype="emergency",
                    tags=frozenset({"emergency", f"squawk_{code}"}),
                    severity=severity,
                )
                if event is None or event.id in seen:
                    continue
                seen.add(event.id)
                events.append(event.with_changes(title=f"{event.title}: squawk {code}, {meaning}"))
        return events


class AdsbAreaConnector:
    """Every aircraft within each watched area, tagged with the area it was seen over."""

    spec = AREAS

    def __init__(
        self, http: FeedHttpClient, clock: Clock, areas: Sequence[WatchArea] | None = None
    ) -> None:
        self._http = http
        self._clock = clock
        self._areas = tuple(areas) if areas is not None else load_watch_areas()

    @property
    def areas(self) -> tuple[WatchArea, ...]:
        return self._areas

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        events: dict[str, Event] = {}
        for area in self._areas:
            try:
                data = await self._http.get_json(area.url, conditional=False)
            except (FeedFetchError, NotModified):
                continue
            for item in records(data):
                event = aircraft_event(
                    self.spec,
                    item,
                    now,
                    subtype="aircraft",
                    tags=frozenset({"area_watch", f"area_{area.id}"}),
                )
                if event is not None and event.id not in events:
                    events[event.id] = event
        return list(events.values())
