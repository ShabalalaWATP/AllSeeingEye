"""Emergency squawks and area traffic from adsb.lol: what the aviation tracker watches for.

The squawk connector asks for 7700 (general emergency), 7600 (radio failure) and 7500
(unlawful interference) each poll. The area connector asks for every aircraft within a
radius of each watched area (docs/04 section 5.3), which is how civil traffic over the
tension areas reaches the globe without any key.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass

# Requires Python >=3.12; this standard-library API is supported.
# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from importlib import resources
from typing import Any

from ase.adapters.feeds.adsb import adsb_spec, aircraft_event, records
from ase.adapters.feeds.adsb_classification import AircraftClassificationCache
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import Event, Reliability

SQUAWKS: dict[str, tuple[str, float]] = {
    "7500": ("unlawful interference", 0.95),
    "7700": ("general emergency", 0.8),
    "7600": ("radio failure", 0.6),
}
MAX_RADIUS_NM = 250
MAX_AREA_EVENTS = 15_000
AREA_FETCH_BUDGET_SECONDS = 45.0
AREA_REQUEST_TIMEOUT_SECONDS = 5.0
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

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        *,
        classifications: AircraftClassificationCache | None = None,
    ) -> None:
        self._http = http
        self._clock = clock
        self._classifications = classifications or AircraftClassificationCache()

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
                events.append(
                    self._classifications.enrich(event, now).with_changes(
                        title=f"{event.title}: squawk {code}, {meaning}"
                    )
                )
        return events


class AdsbAreaConnector:
    """Every aircraft within each watched area, tagged with the area it was seen over."""

    spec = AREAS

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        areas: Sequence[WatchArea] | None = None,
        *,
        classifications: AircraftClassificationCache | None = None,
    ) -> None:
        self._http = http
        self._clock = clock
        self._areas = tuple(areas) if areas is not None else load_watch_areas()
        self._classifications = classifications or AircraftClassificationCache()
        self._start_area = 0
        self._warning: str | None = None

    @property
    def areas(self) -> tuple[WatchArea, ...]:
        return self._areas

    @property
    def warning(self) -> str | None:
        return self._warning

    def request_retry(self) -> None:
        """The scheduler controls retries; retain the bounded regional rotation."""

    async def fetch(self) -> list[Event]:
        self._warning = None
        events: dict[str, Event] = {}
        start = self._start_area
        areas = self._areas[start:] + self._areas[:start]
        deadline = asyncio.get_running_loop().time() + AREA_FETCH_BUDGET_SECONDS
        successful = attempted = 0
        for offset, area in enumerate(areas):
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0 or len(events) >= MAX_AREA_EVENTS:
                break
            attempted += 1
            # Continue after the last attempted region next time, including timeouts.
            self._start_area = (start + offset + 1) % len(self._areas)
            try:
                async with asyncio.timeout(min(AREA_REQUEST_TIMEOUT_SECONDS, remaining)):
                    data = await self._http.get_json(area.url, conditional=False)
            except (FeedFetchError, NotModified, TimeoutError):
                continue
            successful += 1
            now = self._clock.now()  # Anchor reported position age to this response.
            for index, item in enumerate(records(data)):
                event = aircraft_event(
                    self.spec,
                    item,
                    now,
                    subtype="aircraft",
                    tags=frozenset({"area_watch", f"area_{area.id}"}),
                )
                if event is not None and event.id not in events and len(events) < MAX_AREA_EVENTS:
                    events[event.id] = self._classifications.enrich(event, now)
                if index % 250 == 249:
                    await asyncio.sleep(0)
                    if asyncio.get_running_loop().time() >= deadline:
                        break
        if successful < len(areas) or len(events) >= MAX_AREA_EVENTS:
            self._warning = (
                f"Partial regional coverage: {successful}/{len(areas)} areas retrieved; "
                "remaining or unavailable regions rotate through subsequent polls."
            )
        if attempted == len(areas) and areas:
            self._start_area = (start + 1) % len(areas)
        if attempted and not successful:
            raise FeedFetchError("ADS-B regional queries returned no successful responses.")
        return list(events.values())
