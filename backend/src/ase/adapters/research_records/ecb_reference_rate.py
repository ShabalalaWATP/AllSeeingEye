"""One bounded ECB daily reference-rate series, selected by exact subject.

API: https://data.ecb.europa.eu/help/api/data
Reuse: https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html
"""

import asyncio
import csv
import io
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.http_contracts import FeedFetchError, NotModified
from ase.adapters.research_records.records import receipt, record_event, text
from ase.application.ports import Clock
from ase.domain.events import Category, Event, Reliability
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.observation import ObservationMetadata
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

API = "https://data-api.ecb.europa.eu/service/data/EXR/D.GBP.EUR.SP00.A"
SERIES = "EXR.D.GBP.EUR.SP00.A"
LICENCE_URL = (
    "https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/"
    "html/usage_policy.en.html"
)
MAX_DAYS = 31
MAX_BYTES = 64 * 1024
MAX_ROWS = 31
REQUIRED = {
    "KEY",
    "FREQ",
    "CURRENCY",
    "CURRENCY_DENOM",
    "EXR_TYPE",
    "EXR_SUFFIX",
    "TIME_PERIOD",
    "OBS_VALUE",
    "UNIT",
    "UNIT_MULT",
    "OBS_STATUS",
}
LIMITATIONS = (
    "ECB EXR daily GBP per EUR reference rates for the selected date interval only. "
    "At most 31 days and one request, without pagination or automatic series discovery. "
    "Reference dates are not publication timestamps. Weekends and missing rows are not zero. "
    "Rates are information-only, not necessarily transaction prices. This is the current "
    "data vintage; prior revisions and release timestamps are not retrieved. Source: ECB "
    "statistics. Public ESCB data reuse requires attribution and unmodified values/metadata."
)


class EcbReferenceRateProvider:
    id = "research-ecb-gbp-reference-rate"
    name = "ECB GBP per EUR daily reference rates"
    temporal_scope = "At most 31 days of current daily reference-rate values."

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        return bool(
            query.focus is ResearchFocus.GENERAL
            and query.subject == "ECB:EXR:GBP"
            and query.effective_time_basis is EvidenceTimeBasis.RECORDED
            and query.country_isos in ((), ("GB",))
            and query.area is None
            and query.since.astimezone(UTC).time() == datetime.min.time()
            and query.until.astimezone(UTC).time() == datetime.min.time()
            and query.until - query.since <= timedelta(days=MAX_DAYS)
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select ECB:EXR:GBP with recorded UTC day boundaries, no area, and at "
                "most 31 days. "
                "Only GB country context is supported; no request was made.",
            )
        start = query.since.astimezone(UTC).date()
        end = (query.until.astimezone(UTC) - timedelta(microseconds=1)).date()
        url = (
            API
            + "?"
            + urlencode(
                {
                    "startPeriod": start.isoformat(),
                    "endPeriod": end.isoformat(),
                    "format": "csvdata",
                }
            )
        )
        try:
            async with asyncio.timeout(20):
                raw = await self._http.get_bytes(url, conditional=False, max_redirects=0)
            if len(raw) > MAX_BYTES:
                raise ValueError("ECB response exceeds parser byte ceiling")
            items = self._parse(raw, query, url)
        except TimeoutError:
            return receipt(self.id, self.name, CollectionStatus.TIMED_OUT, "ECB request timed out.")
        except (FeedFetchError, NotModified, ValueError, UnicodeError, OverflowError):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "ECB returned unavailable or invalid reference-rate data; "
                "no coverage was established.",
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            LIMITATIONS,
            items,
        )

    def _parse(self, raw: bytes, query: ResearchQuery, url: str) -> list[Event]:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict")))
        if (
            not reader.fieldnames
            or len(reader.fieldnames) > 64
            or not set(reader.fieldnames) >= REQUIRED
        ):
            raise ValueError("Missing ECB reference-rate dimensions")
        rows = list(reader)
        if len(rows) > MAX_ROWS or any(None in row for row in rows):
            raise ValueError("Invalid ECB row count or columns")
        items: list[Event] = []
        seen: set[str] = set()
        now = self._clock.now()
        for row in rows:
            if (
                row["KEY"] != SERIES
                or row["FREQ"] != "D"
                or row["CURRENCY"] != "GBP"
                or row["CURRENCY_DENOM"] != "EUR"
                or row["EXR_TYPE"] != "SP00"
                or row["EXR_SUFFIX"] != "A"
                or row["UNIT"] != "GBP"
                or row["UNIT_MULT"] != "0"
            ):
                raise ValueError("Unexpected ECB series or unit")
            period = row["TIME_PERIOD"]
            if not isinstance(period, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", period):
                raise ValueError("Invalid ECB day")
            day = datetime.fromisoformat(period).replace(tzinfo=UTC)
            if period in seen or not query.since <= day < query.until:
                raise ValueError("Duplicate or out-of-range ECB day")
            seen.add(period)
            lexical = row["OBS_VALUE"]
            if lexical in (None, ""):
                value = None
            else:
                try:
                    decimal = Decimal(lexical)
                except InvalidOperation as exc:
                    raise ValueError("Invalid ECB value") from exc
                if not decimal.is_finite() or not 0 <= decimal <= 1_000_000:
                    raise ValueError("Invalid ECB value")
                value = float(decimal)
            status = row["OBS_STATUS"]
            if status is None or len(status) > 24:
                raise ValueError("Invalid ECB observation status")
            event = record_event(
                self.id,
                f"{SERIES}:{period}",
                f"ECB GBP per EUR reference rate: {period}",
                f"ECB EXR series {SERIES} recorded {'missing' if value is None else lexical} "
                f"GBP per EUR for {period}. Observation status {status or 'not supplied'}. "
                "This reference date is not a publication timestamp or market transaction. "
                "Source: ECB statistics.",
                url,
                now,
                category=Category.ECONOMIC,
                attributes={
                    "record_kind": "daily_reference_rate",
                    "dataset_id": "EXR",
                    "series_id": SERIES,
                    "observation_period": period,
                    "value": value,
                    "missing_value": value is None,
                    "unit": "GBP per EUR",
                    "frequency": "daily",
                    "observation_status": status or None,
                    "unit_multiplier": 0,
                    "observation_confidentiality": text(row.get("OBS_CONF"), 24) or None,
                    "source_agency": text(row.get("SOURCE_AGENCY"), 40) or None,
                    "source_title": text(row.get("TITLE_COMPL"), 300) or None,
                    "seasonal_adjustment": "not_applicable",
                    "vintage": "current_api_snapshot",
                    "revision_time": None,
                    "publisher": "European Central Bank",
                    "licence_url": LICENCE_URL,
                },
            )
            items.append(
                replace(
                    event,
                    published_at=None,
                    observation=ObservationMetadata(
                        acquired_at=day,
                        collection_id=SERIES,
                        item_id=period,
                        limitations="Reference date anchor, not publication or transaction time.",
                    ),
                    reliability=Reliability.F,
                    grade_rationale="Official statistical observation; interpretation unassessed.",
                )
            )
        return sorted(
            items, key=lambda item: item.observation.acquired_at if item.observation else now
        )
