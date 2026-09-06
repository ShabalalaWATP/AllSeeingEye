"""OONI country/day counters only, never individual probe measurements.

API schema: https://api.ooni.io/apispec_1.json
Data licence: https://github.com/ooni/license/blob/master/data/LICENSE.md
"""

import asyncio
import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.adapters.research_records.records import receipt, record_event
from ase.application.ports import Clock
from ase.domain.events import Category, Event, GeoConfidence, Reliability
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery

API = "https://api.ooni.io/api/v1/aggregation"
LICENCE = "CC BY-NC-SA 4.0"
LICENCE_URL = "https://github.com/ooni/license/blob/master/data/LICENSE.md"
MAX_DAYS = 14
MAX_BUCKETS = 15
MAX_JSON_BYTES = 64 * 1024
COUNTS = ("anomaly_count", "confirmed_count", "failure_count", "ok_count", "measurement_count")
LIMITATIONS = (
    "OONI web-connectivity country/day aggregates only, at most 14 days and 15 buckets. "
    "Counts describe contributed tests, not unique people, devices or population coverage. "
    "Anomalies can include false positives; upstream confirmed labels are OONI classifications, "
    "not this app's verification. Counts do not establish censorship, attribution or cause. "
    "Missing days mean no returned coverage, not normal connectivity. "
    "Attribution: Open Observatory of Network Interference (OONI); CC BY-NC-SA 4.0."
)


class OoniAggregateProvider:
    id = "research-ooni-aggregate"
    name = "OONI country connectivity aggregates"
    language = "en"
    temporal_scope = "Daily measurement counters in an explicit interval of at most 14 days."

    def __init__(
        self, http: FeedHttpClient, clock: Clock, *, allow_noncommercial_data: bool = False
    ) -> None:
        self._http, self._clock = http, clock
        self._allowed = allow_noncommercial_data

    def _country(self, query: ResearchQuery) -> str | None:
        subject = re.fullmatch(r"ooni:([A-Za-z]{2})", (query.subject or "").strip())
        if subject:
            country = subject[1].upper()
            return (
                country if not query.country_iso or country == query.country_iso.upper() else None
            )
        if query.source_ids and self.id in query.source_ids:
            value = (query.country_iso or "").upper()
            return value if re.fullmatch(r"[A-Z]{2}", value) else None
        return None

    def supports(self, query: ResearchQuery) -> bool:
        return self._country(query) is not None and query.until - query.since <= timedelta(
            days=MAX_DAYS
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        country = self._country(query)
        if country is None or not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select this source with a two-letter country code, or supply ooni:CC. "
                "The requested interval must be at most 14 days; no request was made.",
            )
        if not self._allowed:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "OONI data collection needs operator acknowledgement of its "
                "Attribution-NonCommercial-ShareAlike 4.0 licence. No request was made.",
            )
        url = (
            API
            + "?"
            + urlencode(
                {
                    "probe_cc": country,
                    "test_name": "web_connectivity",
                    "since": query.since.astimezone(UTC).isoformat().replace("+00:00", ""),
                    "until": query.until.astimezone(UTC).isoformat().replace("+00:00", ""),
                    "axis_x": "measurement_start_day",
                    "time_grain": "day",
                }
            )
        )
        try:
            async with asyncio.timeout(20):
                raw = await self._http.get_bytes(url, conditional=False, max_redirects=0)
            # Transport already caps the body at 5 MiB. Refuse oversized aggregate JSON
            # before decoding; this endpoint should return only a handful of counters.
            if len(raw) > MAX_JSON_BYTES:
                raise ValueError("Aggregate response exceeds parser byte ceiling")
            data = json.loads(raw)
            items = self._parse(data, country, query, url)
        except TimeoutError:
            return receipt(
                self.id, self.name, CollectionStatus.TIMED_OUT, "OONI aggregate request timed out."
            )
        except (
            FeedFetchError,
            NotModified,
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
            RecursionError,
        ):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "OONI aggregate data was unavailable or invalid; no coverage was established.",
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            LIMITATIONS,
            items,
        )

    def _parse(self, data: Any, country: str, query: ResearchQuery, url: str) -> list[Event]:
        if not isinstance(data, dict) or data.get("dimension_count") != 1:
            raise ValueError("Expected one-dimensional country/day aggregation")
        rows = data.get("result")
        if not isinstance(rows, list) or len(rows) > MAX_BUCKETS:
            raise ValueError("Invalid aggregate bucket count")
        items: list[Event] = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid aggregate row")
            date = row["measurement_start_day"]
            if not isinstance(date, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date):
                raise ValueError("Invalid aggregate date")
            day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
            if date in seen or day >= query.until or day + timedelta(days=1) <= query.since:
                raise ValueError("Duplicate or out-of-interval bucket")
            seen.add(date)
            counts = {key: row[key] for key in COUNTS}
            if any(
                type(value) is not int or not 0 <= value <= 1_000_000_000
                for value in counts.values()
            ):
                raise ValueError("Invalid counters")
            total = counts["measurement_count"]
            if sum(counts[key] for key in COUNTS[:-1]) != total:
                raise ValueError("Inconsistent count denominator")
            if not total:
                continue
            start, end = max(day, query.since), min(day + timedelta(days=1), query.until)
            event = record_event(
                self.id,
                f"{country}:{start.isoformat()}:{end.isoformat()}",
                f"OONI {country}: {total} web-connectivity measurements on {date}",
                f"OONI reports {total} tests: {counts['anomaly_count']} anomalous, "
                f"{counts['confirmed_count']} upstream-confirmed, "
                f"{counts['failure_count']} failed, "
                f"{counts['ok_count']} OK. Measurement interval {start.isoformat()} to "
                f"{end.isoformat()} (exclusive). These are tests, not people or population "
                "coverage; categories do not establish cause. OONI, CC BY-NC-SA 4.0.",
                url,
                self._clock.now(),
                category=Category.CYBER,
                published=start,
                attributes={
                    **counts,
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "record_kind": "country_measurement_aggregate",
                    "test_name": "web_connectivity",
                    "date_precision": "day_bucket",
                    "licence": LICENCE,
                    "licence_url": LICENCE_URL,
                    "publisher": "Open Observatory of Network Interference",
                    "denominator": "tests, not people",
                },
            )
            items.append(
                replace(
                    event,
                    reliability=Reliability.F,
                    country_iso=country,
                    geo_confidence=GeoConfidence.COUNTRY,
                    grade_rationale=(
                        "OONI-reported aggregate observations; inference and cause unassessed."
                    ),
                )
            )
        return sorted(items, key=lambda event: event.published_at)
