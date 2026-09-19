"""Emergency squawks and area traffic from adsb.lol: what the aviation tracker watches for.

The squawk connector asks for 7700 (general emergency), 7600 (radio failure) and 7500
(unlawful interference) each poll. The area connector asks for every aircraft within a
radius of each watched area (docs/04 section 5.3), which is how civil traffic over the
tension areas reaches the globe without any key.
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

# Requires Python >=3.12; this standard-library API is supported.
# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from importlib import resources
from typing import Any

from ase.adapters.feeds.adsb import adsb_spec, aircraft_event, records
from ase.adapters.feeds.adsb_classification import AircraftClassificationCache
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, FeedHttpStatusError, NotModified
from ase.adapters.feeds.http_contracts import FeedRateLimitedError
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
        self._warning: str | None = None
        self._start_squawk = 0

    @property
    def warning(self) -> str | None:
        return self._warning

    async def fetch(self) -> list[Event]:
        self._warning = None
        now = self._clock.now()
        events: list[Event] = []
        seen: set[str] = set()
        successful = 0
        start = self._start_squawk
        codes = tuple(SQUAWKS.items())
        for offset, (code, (meaning, severity)) in enumerate(codes[start:] + codes[:start]):
            self._start_squawk = (start + offset + 1) % len(codes)
            try:
                data = await self._http.get_json(
                    f"https://api.adsb.lol/v2/sqk/{code}", conditional=False
                )
            except FeedRateLimitedError as exc:
                self._warning = (
                    f"Partial emergency coverage: {successful}/{len(SQUAWKS)} queries retrieved; "
                    "HTTP 429 paused the remaining queries."
                )
                if not successful:
                    raise FeedRateLimitedError(self.spec.url, exc.retry_after) from None
                break
            except (FeedFetchError, NotModified):
                continue
            successful += 1
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
        max_areas_per_poll: int | None = None,
        request_interval: float = 0.0,
    ) -> None:
        self._http = http
        self._clock = clock
        self._max_areas_per_poll = max_areas_per_poll
        self._request_interval = request_interval
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
        if self._max_areas_per_poll is not None:
            areas = areas[: self._max_areas_per_poll]
        deadline = asyncio.get_running_loop().time() + AREA_FETCH_BUDGET_SECONDS
        successful = attempted = 0
        limited: FeedRateLimitedError | None = None
        statuses: Counter[int] = Counter()
        for offset, area in enumerate(areas):
            if offset and self._request_interval:
                await asyncio.sleep(
                    min(
                        self._request_interval, max(0, deadline - asyncio.get_running_loop().time())
                    )
                )
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0 or len(events) >= MAX_AREA_EVENTS:
                break
            attempted += 1
            # Continue after the last attempted region next time, including timeouts.
            self._start_area = (start + offset + 1) % len(self._areas)
            try:
                async with asyncio.timeout(min(AREA_REQUEST_TIMEOUT_SECONDS, remaining)):
                    data = await self._http.get_json(area.url, conditional=False)
            except FeedRateLimitedError as exc:
                _record_http_status(statuses, 429)
                limited = exc
                break
            except FeedHttpStatusError as exc:
                # Retain only validated numeric codes, never exception URLs or bodies.
                _record_http_status(statuses, exc.status_code)
                continue
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
        diagnostics, self._warning = _area_diagnostics(
            attempted, successful, len(areas), len(events), statuses
        )
        if attempted == len(self._areas) and areas:
            self._start_area = (start + 1) % len(areas)
        _raise_if_no_area_responses(attempted, successful, diagnostics, self.spec.url, limited)
        return list(events.values())


def _raise_if_no_area_responses(
    attempted: int,
    successful: int,
    diagnostics: str,
    url: str,
    limited: FeedRateLimitedError | None,
) -> None:
    if attempted and not successful:
        if limited is not None:
            raise FeedRateLimitedError(url, limited.retry_after) from None
        raise FeedFetchError(
            "ADS-B regional queries returned no successful responses. " + diagnostics
        )


def _area_diagnostics(
    attempted: int, successful: int, total: int, event_count: int, statuses: Counter[int]
) -> tuple[str, str | None]:
    diagnostics = (
        f"{attempted - successful} failed queries; {total - attempted} unattempted; "
        f"{event_count} valid aircraft retained."
    )
    if statuses:
        diagnostics += (
            " HTTP statuses: "
            + ", ".join(f"{code} ({count})" for code, count in sorted(statuses.items()))
            + "."
        )
    warning = None
    if successful < total or event_count >= MAX_AREA_EVENTS:
        warning = (
            f"Partial regional coverage: {successful}/{total} areas retrieved; "
            f"{diagnostics} Remaining or unavailable regions rotate through subsequent polls."
        )
    elif successful and not event_count:
        warning = (
            f"{successful}/{total} regional queries succeeded; "
            "no valid current aircraft positions returned."
        )
    return diagnostics, warning


def _record_http_status(statuses: Counter[int], status: object) -> None:
    if type(status) is int and 100 <= status <= 599:
        statuses[status] += 1
