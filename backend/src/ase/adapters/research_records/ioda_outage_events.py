"""Explicit IODA country outage-window observations, never cyberattack attribution.

API: https://api.ioda.inetintel.cc.gatech.edu/v2/
The live envelope currently carries Georgia Tech copyright, not a general reuse licence.
Collection therefore requires a separate operator data-use acknowledgement.
"""

import asyncio
import json
import math
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.http_contracts import FeedFetchError, NotModified
from ase.adapters.research_records.records import receipt, record_event, text
from ase.application.ports import Clock
from ase.domain.events import Category, Event, GeoConfidence, Reliability
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.observation import ObservationMetadata
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

API = "https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events"
MAX_DAYS = 14
MAX_ITEMS = 20
MAX_BYTES = 64 * 1024
LIMITATIONS = (
    "IODA detected country-level network anomaly windows. One explicit country, at most "
    "14 days and the first 20 returned events; no pagination, complete-history or absence "
    "claim. A returned window can begin before the query and overlap it. Duration describes "
    "the detected window, not affected users or actual service outage duration. A missing "
    "end does not prove an outage is still ongoing. No precise "
    "site, cause, deliberate interference or cyberattack attribution is established. "
    "Source: IODA, Georgia Tech. The API envelope carries copyright; use requires "
    "operator-reviewed permission and attribution."
)


class IodaOutageResearchProvider:
    id = "research-ioda-outage-events"
    name = "IODA country outage event windows"
    temporal_scope = "At most 14 days of detected country anomaly windows, first 20 only."

    def __init__(self, http: FeedHttpClient, clock: Clock, *, allow_data_use: bool = False) -> None:
        self._http, self._clock, self._allowed = http, clock, allow_data_use

    def _country(self, query: ResearchQuery) -> str | None:
        if len(query.country_isos) != 1:
            return None
        country = query.country_isos[0]
        if not re.fullmatch(r"[A-Z]{2}", country):
            return None
        if query.subject == f"IODA:{country}" or (
            query.source_ids is not None and self.id in query.source_ids
        ):
            return country
        return None

    def supports(self, query: ResearchQuery) -> bool:
        return bool(
            query.focus is ResearchFocus.GENERAL
            and query.area is None
            and query.effective_time_basis is EvidenceTimeBasis.RECORDED
            and query.until - query.since <= timedelta(days=MAX_DAYS)
            and self._country(query)
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select one two-letter country and this source or IODA:CC with recorded time "
                "over at most 14 days. No request was made.",
            )
        if not self._allowed:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "IODA public data use needs operator review and acknowledgement before "
                "research collection. No request was made.",
            )
        country = self._country(query)
        if country is None:
            raise ValueError("Supported IODA query has no country")
        start = int(query.since.timestamp())
        end = math.ceil(query.until.timestamp())
        url = (
            API
            + "?"
            + urlencode(
                {
                    "from": start,
                    "until": end,
                    "entityType": "country",
                    "entityCode": country,
                    "limit": MAX_ITEMS,
                }
            )
        )
        try:
            async with asyncio.timeout(20):
                raw = await self._http.get_bytes(url, conditional=False, max_redirects=0)
            if len(raw) > MAX_BYTES:
                raise ValueError("IODA response exceeds parser byte ceiling")
            items = self._parse(json.loads(raw), query, country, start, end, url)
        except TimeoutError:
            return receipt(
                self.id, self.name, CollectionStatus.TIMED_OUT, "IODA request timed out."
            )
        except (FeedFetchError, NotModified, ValueError, TypeError, KeyError, OverflowError):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "IODA returned unavailable or invalid outage data; no coverage was established.",
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            LIMITATIONS,
            items,
        )

    def _parse(
        self,
        data: Any,
        query: ResearchQuery,
        country: str,
        start: int,
        end: int,
        url: str,
    ) -> list[Event]:
        if not isinstance(data, dict) or data.get("type") != "outages.events" or data.get("error"):
            raise ValueError("Invalid IODA envelope")
        params = data.get("requestParameters")
        if not isinstance(params, dict) or any(
            str(params.get(key)) != str(value)
            for key, value in (
                ("from", start),
                ("until", end),
                ("entityType", "country"),
                ("entityCode", country),
                ("limit", MAX_ITEMS),
            )
        ):
            raise ValueError("IODA response does not match the requested scope")
        rows = data.get("data")
        if not isinstance(rows, list) or len(rows) > MAX_ITEMS:
            raise ValueError("Invalid IODA result count")
        now = self._clock.now()
        seen: set[str] = set()
        items: list[Event] = []
        for row in rows:
            if not isinstance(row, dict) or row.get("location") != f"country/{country}":
                raise ValueError("IODA returned a different geography")
            stamp, duration = row.get("start"), row.get("duration")
            if type(stamp) is not int or not 0 < stamp < 4_102_444_800:
                raise ValueError("Invalid IODA event start")
            if duration is not None and (
                not isinstance(duration, int | float)
                or isinstance(duration, bool)
                or not math.isfinite(duration)
                or not 0 <= duration <= 7_776_000
            ):
                raise ValueError("Invalid IODA event duration")
            opened = datetime.fromtimestamp(stamp, tz=UTC)
            closed = opened + timedelta(seconds=duration) if duration is not None else None
            if (
                opened >= query.until
                or (closed is not None and closed <= query.since)
                or (closed is None and opened < query.since)
            ):
                continue
            datasource = text(row.get("datasource"), 32)
            method = text(row.get("method"), 32)
            if not datasource or not method:
                raise ValueError("IODA event lacks signal provenance")
            key = f"{country}:{stamp}:{datasource}:{method}"
            if key in seen:
                raise ValueError("Duplicate IODA event")
            seen.add(key)
            name = text(row.get("location_name"), 120) or country
            event = record_event(
                self.id,
                key,
                f"IODA network anomaly window: {name} ({datasource})",
                f"IODA detected a {datasource} network anomaly for country {country}, "
                f"starting {opened.isoformat()} and "
                f"ending {closed.isoformat() if closed else 'at an unknown time'}. "
                "This signal does not establish affected users, a precise site, cause, "
                "deliberate interference or a cyberattack. Source: IODA, Georgia Tech.",
                f"https://ioda.inetintel.cc.gatech.edu/country/{country}",
                now,
                category=Category.CYBER,
                attributes={
                    "record_kind": "country_outage_detection_window",
                    "dataset_id": "IODA outages.events v2",
                    "country_code": country,
                    "signal": datasource,
                    "method": method,
                    "window_start": opened.isoformat(),
                    "window_end": closed.isoformat() if closed else None,
                    "duration_seconds": float(duration) if duration is not None else None,
                    "unit": "seconds",
                    "geography_precision": "country",
                    "retrieval_url": url,
                    "publisher": "Georgia Tech Internet Intelligence Lab",
                    "copyright": text(data.get("copyright"), 200) or None,
                },
            )
            items.append(
                replace(
                    event,
                    published_at=None,
                    observation=ObservationMetadata(
                        acquired_at=opened,
                        collection_id="IODA/outages.events/v2",
                        item_id=key,
                        limitations=(
                            "Detected anomaly-window start, not publication or exact outage onset."
                        ),
                    ),
                    country_iso=country,
                    geo_confidence=GeoConfidence.COUNTRY,
                    reliability=Reliability.F,
                    grade_rationale=(
                        "Provider-detected network anomaly; cause and impact unassessed."
                    ),
                )
            )
        return sorted(
            items, key=lambda item: item.observation.acquired_at if item.observation else now
        )
