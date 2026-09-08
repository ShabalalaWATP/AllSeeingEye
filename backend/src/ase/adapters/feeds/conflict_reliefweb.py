"""Bounded ReliefWeb context reports, preserving each original publisher."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.conflict_values import public_link, text, when
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
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

MAX_REPORTS = 100
SPEC = SourceSpec(
    id="reliefweb_reports",
    name="ReliefWeb humanitarian reports (API)",
    organisation="ReliefWeb / UN OCHA",
    category=Category.HUMANITARIAN,
    kind=SourceKind.API,
    url="https://api.reliefweb.int/v2/reports",
    reliability=Reliability.B,
    poll_interval=timedelta(hours=1),
    requires_key=True,
    homepage="https://reliefweb.int/",
    licence_note="Original publishers retain rights; metadata and links only.",
    flags=frozenset({"approved_appname_required", "context_reporting", "aggregator"}),
)


class ReliefWebReportsConnector:
    spec = SPEC

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        appname: str,
        iso3_to_iso2: Mapping[str, str] | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,99}", appname):
            raise ValueError("ReliefWeb requires a pre-approved application name.")
        self._http, self._clock = http, clock
        self._iso3_to_iso2 = dict(iso3_to_iso2 or {})
        params = [("appname", appname), ("limit", str(MAX_REPORTS)), ("preset", "latest")]
        params.extend(
            ("fields[include][]", field)
            for field in ("title", "url", "origin", "date", "source", "country", "primary_country")
        )
        self._url = self.spec.url + "?" + urlencode(params)

    async def fetch(self) -> list[Event]:
        try:
            payload = await self._http.get_json(self._url)
        except NotModified:
            return []
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise FeedFetchError("ReliefWeb returned an invalid report envelope.")
        if len(payload["data"]) > MAX_REPORTS:
            raise FeedFetchError("ReliefWeb returned more reports than requested.")
        now = self._clock.now()
        events: dict[str, Event] = {}
        for row in payload["data"]:
            if isinstance(row, dict) and (event := self._to_event(row, now)):
                events[event.id] = event
        return list(events.values())

    def _to_event(self, row: dict[str, Any], now: datetime) -> Event | None:
        fields = row.get("fields")
        upstream_id = text(row.get("id"), 100)
        if not isinstance(fields, dict) or not upstream_id or not text(fields.get("title")):
            return None
        date = fields.get("date")
        if not isinstance(date, dict):
            date = {}
        primary = fields.get("primary_country")
        if isinstance(primary, list):
            primary = primary[0] if primary else {}
        if not isinstance(primary, dict):
            primary = {}
        countries = fields.get("country")
        if not isinstance(countries, list):
            countries = []
        sources = fields.get("source")
        if not isinstance(sources, list):
            sources = []
        names = [text(source.get("name")) for source in sources[:20] if isinstance(source, dict)]
        country_names = [
            text(country.get("name")) for country in countries[:30] if isinstance(country, dict)
        ]
        return Event(
            id=event_id(self.spec.id, upstream_id),
            source_id=self.spec.id,
            category=Category.HUMANITARIAN,
            subtype="humanitarian_report",
            title=text(fields.get("title"), 300),
            url=public_link(fields.get("url")),
            summary="Report published by "
            + (", ".join(names)[:500] or "an unspecified contributor")
            + "; indexed by ReliefWeb. Context reporting, not a verified incident location.",
            published_at=when(date.get("original")),
            observed_at=now,
            country_iso=self._iso3_to_iso2.get(text(primary.get("iso3")).upper()),
            geo_confidence=GeoConfidence.COUNTRY if primary else GeoConfidence.NONE,
            reliability=self.spec.reliability,
            credibility=Credibility.CANNOT_BE_JUDGED,
            grade_rationale="ReliefWeb indexing does not independently verify the original report.",
            tags=frozenset({"humanitarian", "context_report", "reliefweb"}),
            attributes=freeze_attributes(
                {
                    "upstream_id": upstream_id,
                    "original_publishers": ", ".join(names),
                    "original_url": public_link(fields.get("origin")),
                    "country": text(primary.get("name")),
                    "countries": ", ".join(country_names),
                    "country_iso3": text(primary.get("iso3")),
                    "indexed_at": text(date.get("created")),
                    "provenance_provider": "ReliefWeb",
                    "evidence_kind": "context_report",
                    "coverage_scope": "latest_100_reports",
                    "independence_verified": False,
                }
            ),
            content_hash=content_hash(json.dumps(fields, sort_keys=True)),
        )
