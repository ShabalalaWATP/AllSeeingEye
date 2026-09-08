"""Optional ACLED events using an operator-provisioned, short-lived OAuth token."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
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

ORIGIN = "https://acleddata.com"
PAGE_SIZE = 500
MAX_PAGES = 20
LOOKBACK_DAYS = 14
SPEC = SourceSpec(
    id="acled_events",
    name="ACLED political violence and protest events",
    organisation="ACLED",
    category=Category.CONFLICT,
    kind=SourceKind.API,
    url=ORIGIN + "/api/acled/read",
    reliability=Reliability.B,
    poll_interval=timedelta(hours=6),
    requires_key=True,
    homepage=ORIGIN,
    licence_note="ACLED account entitlement and terms apply; attribution required.",
    flags=frozenset({"account_required", "access_tier_limited", "oauth_token_required"}),
)
TYPES = {
    "Battles": (Category.CONFLICT, "armed_clash"),
    "Explosions/Remote violence": (Category.CONFLICT, "strike"),
    "Violence against civilians": (Category.CONFLICT, "civilian_harm"),
    "Protests": (Category.CONFLICT, "protest"),
    "Riots": (Category.CONFLICT, "riot"),
    "Strategic developments": (Category.CONFLICT, "force_posture"),
}


class AcledConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock, access_token: str) -> None:
        if not access_token.strip():
            raise ValueError("ACLED requires a current OAuth access token.")
        self._http, self._clock = http, clock
        self._credential = FeedCredential(ORIGIN, "Bearer " + access_token)

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        events: dict[str, Event] = {}
        for page in range(1, MAX_PAGES + 1):
            query = urlencode(
                {
                    "_format": "json",
                    "limit": PAGE_SIZE,
                    "page": page,
                    "event_date": (now - timedelta(days=LOOKBACK_DAYS)).date(),
                    "event_date_where": ">=",
                    "export_type": "dyadic",
                }
            )
            payload = await self._http.get_json(
                self.spec.url + "?" + query, credential=self._credential
            )
            if (
                not isinstance(payload, dict)
                or integer(payload.get("status")) != 200
                or not isinstance(payload.get("data"), list)
            ):
                raise FeedFetchError("ACLED data unavailable; check token and account entitlement.")
            rows = payload["data"]
            if len(rows) > PAGE_SIZE:
                raise FeedFetchError("ACLED returned more rows than requested.")
            for index, row in enumerate(rows):
                if isinstance(row, dict) and (event := self._to_event(row, now)):
                    events[event.id] = event
                if index % 250 == 249:
                    await asyncio.sleep(0)
            if len(rows) < PAGE_SIZE:
                return list(events.values())
        raise FeedFetchError("ACLED collection limit reached; coverage is incomplete.")

    def _to_event(self, row: dict[str, Any], now: datetime) -> Event | None:
        upstream_id = text(row.get("event_id_cnty"), 100)
        event_type = text(row.get("event_type"))
        occurred = when(row.get("event_date"))
        if not upstream_id or event_type not in TYPES or occurred is None:
            return None
        if occurred > now or occurred.date() < (now - timedelta(days=LOOKBACK_DAYS)).date():
            return None
        category, subtype = TYPES[event_type]
        position = point(row.get("latitude"), row.get("longitude"))
        precision = integer(row.get("geo_precision"))
        return Event(
            id=event_id(self.spec.id, upstream_id),
            source_id=self.spec.id,
            category=category,
            subtype=subtype,
            title=f"{event_type}: {text(row.get('location'))}, {text(row.get('country'))}"[:300],
            summary=text(row.get("notes"), 2000) or None,
            url=ORIGIN,
            published_at=None,
            observed_at=now,
            point=position,
            geo_confidence=(
                GeoConfidence.CITY
                if precision in {1, 2}
                else GeoConfidence.ADMIN1
                if precision == 3
                else GeoConfidence.NONE
            )
            if position
            else GeoConfidence.NONE,
            reliability=self.spec.reliability,
            credibility=Credibility.POSSIBLY_TRUE,
            grade_rationale="ACLED-coded reporting; account coverage and location precision apply.",
            tags=frozenset({"acled", subtype}),
            attributes=freeze_attributes(
                {
                    "upstream_id": upstream_id,
                    "incident_id": upstream_id,
                    "origin_dataset": "acled",
                    "event_type": event_type,
                    "sub_event_type": text(row.get("sub_event_type")),
                    "occurrence_start": occurred.isoformat(),
                    "occurrence_end": occurred.isoformat(),
                    "date_precision": integer(row.get("time_precision")),
                    "geo_precision": precision,
                    "actor1": text(row.get("actor1")),
                    "actor2": text(row.get("actor2")),
                    "country": text(row.get("country")),
                    "location": text(row.get("location")),
                    "reported_fatalities_best": count(row.get("fatalities")),
                    "fatalities_uncertain_zero": count(row.get("fatalities")) == 0,
                    "reported_fatalities_low": None,
                    "reported_fatalities_high": None,
                    "fatalities_caveat": "Coded zero may include unknown fatalities.",
                    "source_articles": text(row.get("source")),
                    "source_scale": text(row.get("source_scale")),
                    "upstream_updated": text(row.get("timestamp")),
                    "provenance_provider": "ACLED",
                    "evidence_kind": "coded_incident",
                    "independence_verified": False,
                    "coverage_scope": "account_entitlement",
                }
            ),
            content_hash=content_hash(json.dumps(row, sort_keys=True)),
        )
