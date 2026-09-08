"""Versioned UCDP candidate observations, released monthly rather than live."""

from __future__ import annotations

import asyncio
import calendar
import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.conflict_values import count, integer, point, text, when
from ase.adapters.feeds.http import FeedCredential, FeedFetchError, FeedHttpClient
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

ORIGIN = "https://ucdpapi.pcr.uu.se"
PAGE_SIZE = 500
MAX_PAGES = 20
SPEC = SourceSpec(
    id="ucdp_candidate",
    name="UCDP monthly candidate violence events",
    organisation="Uppsala Conflict Data Program",
    category=Category.CONFLICT,
    kind=SourceKind.API,
    url=ORIGIN + "/api/gedevents/26.0.7",
    reliability=Reliability.B,
    poll_interval=timedelta(days=1),
    requires_key=True,
    homepage="https://ucdp.uu.se/downloads/",
    licence_note="CC BY 4.0; cite Hegre et al. (2020), UCDP Candidate Events Dataset.",
    flags=frozenset({"monthly_release", "provisional", "token_required"}),
)
PRECISION = {
    1: GeoConfidence.CITY,
    2: GeoConfidence.CITY,
    3: GeoConfidence.ADMIN1,
    4: GeoConfidence.ADMIN1,
    5: GeoConfidence.COUNTRY,
    6: GeoConfidence.COUNTRY,
}


class UcdpRecords:
    def __init__(self, http: FeedHttpClient, clock: Clock, version: str) -> None:
        if not re.fullmatch(r"[0-9]{2}\.0\.([1-9]|1[0-2])", version):
            raise ValueError("UCDP requires an explicit monthly candidate version YY.0.M.")
        year, _, month = map(int, version.split("."))
        self._coverage_start = datetime(2000 + year, month, 1, tzinfo=UTC)
        self._coverage_end = self._coverage_start.replace(
            day=calendar.monthrange(2000 + year, month)[1]
        )
        self.spec = replace(SPEC, url=ORIGIN + "/api/gedevents/" + version)
        self._http, self._clock, self._version = http, clock, version

    def _to_event(self, row: dict[str, Any], now: datetime) -> Event | None:
        upstream_id = count(row.get("id"))
        violence = integer(row.get("type_of_violence"))
        start, end = when(row.get("date_start")), when(row.get("date_end"))
        if upstream_id is None or violence not in {1, 2, 3} or not start or not end:
            return None
        if start > end or end > now or not self._coverage_start <= end <= self._coverage_end:
            return None
        subtype = "civilian_harm" if violence == 3 else "organised_violence"
        location = text(row.get("where_coordinates")) or text(row.get("country"))
        label = "One-sided violence" if violence == 3 else "Organised violence"
        position = point(row.get("latitude"), row.get("longitude"))
        attrs = {
            "upstream_id": str(upstream_id),
            "incident_id": str(upstream_id),
            "origin_dataset": "ucdp_ged",
            "dataset_version": self._version,
            "coverage_start": self._coverage_start.date().isoformat(),
            "coverage_end": self._coverage_end.date().isoformat(),
            "occurrence_start": start.isoformat(),
            "occurrence_end": end.isoformat(),
            "date_precision": integer(row.get("date_prec")),
            "geo_precision": integer(row.get("where_prec")),
            "type_of_violence": violence,
            "actor1": text(row.get("side_a")),
            "actor2": text(row.get("side_b")),
            "country": text(row.get("country")),
            "location": location,
            "conflict_name": text(row.get("conflict_name")),
            "reported_fatalities_low": count(row.get("low")),
            "reported_fatalities_best": count(row.get("best")),
            "reported_fatalities_high": count(row.get("high")),
            "source_articles": text(row.get("source_article")),
            "source_original": text(row.get("source_original")),
            "provenance_provider": "UCDP",
            "evidence_kind": "coded_incident",
            "dataset_status": "provisional_monthly",
            "independence_verified": False,
        }
        return Event(
            id=event_id(self.spec.id, str(upstream_id)),
            source_id=self.spec.id,
            category=Category.CONFLICT,
            subtype=subtype,
            title=f"{label}: {location}"[:300],
            summary="Provisional UCDP candidate record; occurrence dates precede collection.",
            url="https://ucdp.uu.se/",
            published_at=None,
            observed_at=now,
            point=position,
            geo_confidence=PRECISION.get(integer(row.get("where_prec")) or 0, GeoConfidence.NONE)
            if position
            else GeoConfidence.NONE,
            reliability=self.spec.reliability,
            credibility=Credibility.POSSIBLY_TRUE,
            grade_rationale="Research-coded provisional record; not independent confirmation.",
            tags=frozenset({"ucdp", "monthly_release", "provisional", subtype}),
            attributes=freeze_attributes(attrs),
            content_hash=content_hash(json.dumps(row, sort_keys=True)),
        )


class UcdpCandidateConnector(UcdpRecords):
    def __init__(self, http: FeedHttpClient, clock: Clock, token: str, version: str) -> None:
        super().__init__(http, clock, version)
        self._credential = FeedCredential(ORIGIN, token, header_name="x-ucdp-access-token")

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        events: dict[str, Event] = {}
        for page in range(1, MAX_PAGES + 1):
            query = urlencode(
                {
                    "pagesize": PAGE_SIZE,
                    "page": page,
                    "StartDate": self._coverage_start.date().isoformat(),
                    "EndDate": self._coverage_end.date().isoformat(),
                }
            )
            payload = await self._http.get_json(
                self.spec.url + "?" + query, credential=self._credential
            )
            if not isinstance(payload, dict) or not isinstance(payload.get("Result"), list):
                raise FeedFetchError("UCDP returned an invalid result envelope.")
            pages = count(payload.get("TotalPages"))
            rows = payload["Result"]
            if pages is None or pages > MAX_PAGES or len(rows) > PAGE_SIZE:
                raise FeedFetchError("UCDP result exceeds bounded monthly collection capacity.")
            if not rows and page < pages:
                raise FeedFetchError("UCDP returned an incomplete page.")
            for index, row in enumerate(rows):
                if isinstance(row, dict) and (event := self._to_event(row, now)):
                    events[event.id] = event
                if index % 250 == 249:
                    await asyncio.sleep(0)
            if page >= pages:
                return list(events.values())
        raise FeedFetchError("UCDP pagination did not complete.")
