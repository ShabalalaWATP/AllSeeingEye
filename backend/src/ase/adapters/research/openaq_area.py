"""Bounded, on-demand OpenAQ latest observations within an operator's drawn area."""

import asyncio
from dataclasses import dataclass, field
from functools import partial
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research.hazard_area import receipt, supports
from ase.adapters.research.openaq_client import OpenAqAllowanceError, OpenAqClient
from ase.adapters.research.openaq_records import (
    SOURCE_ID,
    OpenAqArea,
    ReuseLicence,
    applicable_licences,
    identifier,
    measurement,
    rows,
    station,
    station_date,
    to_event,
)
from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.ports import Clock
from ase.domain.events import Event
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchMode, ResearchQuery

MAX_STATIONS = 100
MAX_LICENCES = 4
MAX_MEASUREMENTS = 50
LIMITATIONS = (
    "Partial latest-per-sensor observations, not a complete historical search or area-wide "
    "pollution assessment. One admitted collection task uses up to 11 HTTP requests: "
    "one 100-station page, up to 3 quick/6 detailed stations and 4 licence lookups, with "
    "10s/18s deadlines. Two-second shared pacing; no retries or background polling. "
    "Stationary sensors only, exact area and measurement-date checks. Question/language "
    "terms do not filter this search. Reuse-restricted/missing licences are excluded. "
    "Empty results do not establish clean air or absence of monitoring."
)


@dataclass(slots=True)
class _Run:
    items: dict[str, Event] = field(default_factory=dict)
    licences: dict[int, ReuseLicence | None] = field(default_factory=dict)
    stations_checked: int = 0
    candidates: int = 0
    rejected: int = 0
    licence_excluded: int = 0
    page_limited: bool = False

    def explanation(self) -> str:
        return (
            f"{self.candidates} eligible station candidates; {self.stations_checked} queried. "
            f"{self.rejected} station/readings excluded by validation, area or date; "
            f"{self.licence_excluded} readings excluded by licence checks/budget. "
            + (
                "Catalogue/station page truncated or possibly incomplete. "
                if self.page_limited
                else ""
            )
        )


class OpenAqAreaResearchProvider:
    id = SOURCE_ID
    name = "OpenAQ area air-quality observations"
    spatial_scope = LIMITATIONS
    temporal_scope = "Latest sensor acquisition time within a half-open interval, at most 14 days."

    def __init__(self, http: FeedHttpClient, clock: Clock, api_key: str | None = None) -> None:
        self._client, self._clock = OpenAqClient(http, api_key), clock

    def supports(self, query: ResearchQuery) -> bool:
        return supports(query)

    def supports_area(self, query: ResearchQuery) -> bool:
        return self.supports(query)

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query) or query.area is None:
            return receipt(self.id, self.name, CollectionStatus.UNSUPPORTED, LIMITATIONS)
        if not self._client.configured:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "An OpenAQ API key is not configured; no request was made.",
            )
        state = _Run()
        interruption = ""
        status = CollectionStatus.EMPTY
        try:
            # Finish before the collector's 12s/20s deadline, retaining partial results.
            async with asyncio.timeout(10 if query.mode is ResearchMode.QUICK else 18):
                area = await joined_thread_call(partial(OpenAqArea, query.area))
                await self._collect(query, area, state)
        except OpenAqAllowanceError:
            status, interruption = (
                CollectionStatus.BUDGET_EXHAUSTED,
                "Local request allowance/cooldown reached. ",
            )
        except TimeoutError:
            status, interruption = CollectionStatus.TIMED_OUT, "Collection deadline reached. "
        except Exception:
            # No upstream messages, private area, credential or response bodies in receipts.
            status, interruption = (
                CollectionStatus.FAILED,
                "Upstream data could not be retrieved or validated. ",
            )
        items = tuple(state.items.values())
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else status,
            ("Partial results retained. " if items and interruption else "")
            + interruption
            + state.explanation()
            + LIMITATIONS,
            items,
        )

    async def _collect(self, query: ResearchQuery, area: OpenAqArea, state: _Run) -> None:
        payload = await self._client.get(
            "/v3/locations?"
            + urlencode(
                {
                    "bbox": area.bbox,
                    "mobile": "false",
                    "limit": MAX_STATIONS,
                    "page": 1,
                }
            )
        )
        candidates = rows(payload, MAX_STATIONS)
        found = (
            payload.get("meta", {}).get("found") if isinstance(payload.get("meta"), dict) else None
        )
        state.page_limited = len(candidates) == MAX_STATIONS or (
            found is not None and (type(found) is not int or found > len(candidates))
        )

        def select() -> list[dict[str, Any]]:
            accepted: dict[int, dict[str, Any]] = {}
            for raw in candidates:
                try:
                    value = station(raw, area)
                except (ValueError, TypeError, OverflowError):
                    value = None
                if value is None:
                    state.rejected += 1
                else:
                    accepted[value["id"]] = value
            # Only prioritisation. Every actual sensor timestamp is checked separately.
            return sorted(accepted.values(), key=station_date, reverse=True)

        selected = await joined_thread_call(select)
        state.candidates = len(selected)
        limit = 3 if query.mode is ResearchMode.QUICK else 6
        state.page_limited |= len(selected) > limit
        for location in selected[:limit]:
            state.stations_checked += 1
            payload = await self._client.get(
                f"/v3/locations/{location['id']}/latest?"
                + urlencode(
                    {
                        "limit": MAX_MEASUREMENTS,
                        "page": 1,
                        "datetime_min": query.since.isoformat(),
                    }
                )
            )
            observations = rows(payload, MAX_MEASUREMENTS)
            state.page_limited |= len(observations) == MAX_MEASUREMENTS
            for raw in observations:
                try:
                    parsed = measurement(raw, location, query, area, self._clock.now())
                    applicable = applicable_licences(location, parsed[0])
                except (ValueError, TypeError, KeyError, OverflowError):
                    state.rejected += 1
                    continue
                licences = await self._licences(applicable, state)
                if not licences:
                    state.licence_excluded += 1
                    continue
                try:
                    event = to_event(raw, location, *parsed, licences, self._clock.now())
                except (ValueError, TypeError, KeyError, OverflowError):
                    state.rejected += 1
                    continue
                state.items[event.id] = event

    async def _licences(
        self,
        applicable: list[dict[str, Any]],
        state: _Run,
    ) -> list[tuple[dict[str, Any], ReuseLicence]]:
        admitted = []
        for scope in applicable:
            key = identifier(scope["id"])
            if key not in state.licences:
                if len(state.licences) >= MAX_LICENCES:
                    return []
                state.licences[key] = ReuseLicence.parse(
                    await self._client.get(f"/v3/licenses/{key}"),
                    key,
                )
            licence = state.licences[key]
            if licence is None:
                return []
            admitted.append((scope, licence))
        return admitted
