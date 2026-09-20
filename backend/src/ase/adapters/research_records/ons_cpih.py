"""Bounded UK CPIH observations from one fixed ONS dataset and series.

Official API guide: https://developer.ons.gov.uk/observations/cmd/
Rate guidance: https://developer.ons.gov.uk/bots/
"""

import asyncio
import json
import math
import re
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit

from ase.adapters.feeds.http import FeedFetchError, NotModified
from ase.adapters.research_records.records import receipt, record_event, text
from ase.application.ports import Clock
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.events import Category, Event, GeoConfidence, Reliability
from ase.domain.evidence_time import EvidenceTimeBasis, publication_order
from ase.domain.observation import ObservationMetadata
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

PROVIDER_ID = "research-ons-cpih"
PROVIDER_NAME = "ONS UK Consumer Prices Index including owner occupiers' housing costs"
DATASET_ID = "cpih01"
EDITION = "time-series"
GEOGRAPHY = "K02000001"
AGGREGATE = "cpih1dim1A0"
API = f"https://api.beta.ons.gov.uk/v1/datasets/{DATASET_ID}"
LICENCE = "Open Government Licence v3.0"
LICENCE_URL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
MAX_MONTHS = 24
MAX_RESPONSE_ROWS = 600
MAX_JSON_BYTES = 256 * 1024
_SUBJECT = re.compile(r"ONS:CPIH:([1-9][0-9]{0,8})")
_MONTH = re.compile(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-([0-9]{2})")
_MONTHS = {
    name: number
    for number, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        1,
    )
}
LIMITATIONS = (
    "Office for National Statistics CPIH all-items index for the United Kingdom only. "
    "At most 24 monthly observations are selected from one explicit ONS dataset version. "
    "The caller-selected version is not a freshness claim; ONS can revise values in later "
    "versions. Observation months are not publication dates. Missing values remain null "
    "and are not treated as zero. Source: Office for National Statistics, licensed under the "
    "Open Government Licence v3.0."
)


class BytesReader(Protocol):
    async def get_bytes(
        self, url: str, *, conditional: bool = True, max_redirects: int = 3
    ) -> bytes: ...


def _month_start(value: datetime) -> datetime:
    return datetime(value.year, value.month, 1, tzinfo=UTC)


def _next_month(value: datetime) -> datetime:
    return datetime(
        value.year + (1 if value.month == 12 else 0),
        1 if value.month == 12 else value.month + 1,
        1,
        tzinfo=UTC,
    )


def _month_count(query: ResearchQuery) -> int:
    first = _month_start(query.since.astimezone(UTC))
    cursor, count = first, 0
    while cursor < query.until.astimezone(UTC) and count <= MAX_MONTHS:
        count += 1
        cursor = _next_month(cursor)
    return count


def _version_href(value: object, version: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parts = urlsplit(value)
        return (
            parts.scheme == "https"
            and parts.hostname == "api.beta.ons.gov.uk"
            and parts.port in (None, 443)
            and parts.username is None
            and parts.password is None
            and parts.query == ""
            and parts.fragment == ""
            and parts.path == f"/v1/datasets/{DATASET_ID}/editions/{EDITION}/versions/{version}"
        )
    except ValueError:
        return False


def _dimension_id(dimensions: dict[str, Any], name: str) -> str | None:
    dimension = dimensions.get(name)
    option = dimension.get("option") if isinstance(dimension, dict) else None
    value = option.get("id") if isinstance(option, dict) else None
    return value if isinstance(value, str) else None


def _time_options(dimensions: dict[str, Any]) -> list[Any]:
    dimension = dimensions.get("time")
    options = dimension.get("options") if isinstance(dimension, dict) else None
    if not isinstance(options, list):
        raise ValueError("ONS response has no time options")
    return options


def _period(value: object) -> tuple[str, datetime, datetime]:
    if not isinstance(value, dict) or not isinstance(value.get("id"), str):
        raise ValueError("Invalid ONS time option")
    label = value["id"]
    match = _MONTH.fullmatch(label)
    if match is None:
        raise ValueError("Invalid ONS monthly period")
    short_year = int(match[2])
    year = (2000 if short_year <= 69 else 1900) + short_year
    start = datetime(year, _MONTHS[match[1]], 1, tzinfo=UTC)
    return label, start, _next_month(start)


def _numeric(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, str | int | float) or isinstance(value, bool):
        raise ValueError("Invalid ONS observation")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("Invalid ONS observation") from None
    if not math.isfinite(number) or abs(number) > 1e12:
        raise ValueError("Invalid ONS observation")
    return number


class OnsCpihProvider:
    id = PROVIDER_ID
    name = PROVIDER_NAME
    language = "en"
    temporal_scope = "One explicit ONS version, at most 24 bounded monthly observations."

    def __init__(self, http: BytesReader, clock: Clock) -> None:
        self._http, self._clock = http, clock

    @staticmethod
    def _version(query: ResearchQuery) -> str | None:
        match = _SUBJECT.fullmatch((query.subject or "").strip())
        return match[1] if match else None

    def supports(self, query: ResearchQuery) -> bool:
        return bool(
            query.focus is ResearchFocus.GENERAL
            and self._version(query) is not None
            and query.effective_time_basis is EvidenceTimeBasis.RECORDED
            and (not query.country_isos or query.country_isos == ("GB",))
            and 1 <= _month_count(query) <= MAX_MONTHS
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply subject ONS:CPIH:<version> with a positive numeric ONS version, United "
                "Kingdom or no country filter, recorded-time basis, and at most 24 months; "
                "no request was made.",
            )
        version = self._version(query)
        if version is None:
            raise AssertionError("Supported ONS query has no version")
        try:
            async with asyncio.timeout(20):
                query_string = urlencode(
                    {"time": "*", "geography": GEOGRAPHY, "aggregate": AGGREGATE}
                )
                url = f"{API}/editions/{EDITION}/versions/{version}/observations?{query_string}"
                observations = await self._read(url)
            items = self._parse(observations, version, query, url)
        except TimeoutError:
            return receipt(
                self.id, self.name, CollectionStatus.TIMED_OUT, "ONS CPIH request timed out."
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
                "ONS CPIH data was unavailable or invalid; no coverage was established.",
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            LIMITATIONS,
            items,
        )

    async def _read(self, url: str) -> Any:
        raw = await self._http.get_bytes(url, conditional=False, max_redirects=0)
        if len(raw) > MAX_JSON_BYTES:
            raise ValueError("ONS response exceeds parser byte ceiling")
        return json.loads(raw)

    def _parse(
        self,
        data: Any,
        version: str,
        query: ResearchQuery,
        url: str,
    ) -> list[Event]:
        if not isinstance(data, dict) or data.get("offset") != 0:
            raise ValueError("Invalid ONS observations response")
        links, dimensions = data.get("links"), data.get("dimensions")
        if not isinstance(links, dict) or not isinstance(dimensions, dict):
            raise ValueError("Invalid ONS observations metadata")
        version_link = links.get("version")
        if (
            not isinstance(version_link, dict)
            or version_link.get("id") != version
            or not _version_href(version_link.get("href"), version)
            or _dimension_id(dimensions, "aggregate") != AGGREGATE
            or _dimension_id(dimensions, "geography") != GEOGRAPHY
        ):
            raise ValueError("ONS observations do not match the requested series")
        observations, options = data.get("observations"), _time_options(dimensions)
        total = data.get("total_observations")
        if (
            not isinstance(observations, list)
            or type(total) is not int
            or total != len(observations)
            or len(options) != total
            or not 1 <= total <= MAX_RESPONSE_ROWS
        ):
            raise ValueError("Invalid ONS observation count")
        unit = text(data.get("unit_of_measure"), 120)
        if not unit:
            raise ValueError("ONS observations have no unit")
        now, seen, items = self._clock.now(), set(), []
        for option, row in zip(options, observations, strict=True):
            label, start, end = _period(option)
            if label in seen:
                raise ValueError("Duplicate ONS observation period")
            seen.add(label)
            if not isinstance(row, dict) or "observation" not in row:
                raise ValueError("Invalid ONS observation row")
            value = _numeric(row["observation"])
            if start >= query.until or end <= query.since:
                continue
            display = "missing" if value is None else f"{value:g}"
            event = record_event(
                self.id,
                f"{DATASET_ID}:{version}:{label}",
                f"UK CPIH all-items index: {label}",
                f"ONS CPIH all-items index for {label}: {display} {unit}. "
                f"Dataset {DATASET_ID}, edition {EDITION}, version {version}. "
                "The observation month is not its publication date; later ONS versions may revise "
                "this value. Missing is not zero. Source: Office for National Statistics, "
                "OGL v3.0.",
                url,
                now,
                category=Category.ECONOMIC,
                attributes={
                    "record_kind": "monthly_index_observation",
                    "dataset_id": DATASET_ID,
                    "edition": EDITION,
                    "dataset_version": version,
                    "series_id": AGGREGATE,
                    "observation_period": label,
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "value": value,
                    "missing_value": value is None,
                    "unit": unit,
                    "frequency": "monthly",
                    "geography": GEOGRAPHY,
                    "publisher": "Office for National Statistics",
                    "licence": LICENCE,
                    "licence_url": LICENCE_URL,
                },
            )
            items.append(
                replace(
                    event,
                    published_at=None,
                    observation=ObservationMetadata(
                        acquired_at=start,
                        collection_id=f"{DATASET_ID}/{EDITION}/{version}/{AGGREGATE}",
                        item_id=label,
                        limitations=(
                            "Acquisition time represents the start of the published statistical "
                            "reference month, not a measurement, occurrence or publication "
                            "instant. "
                            "Exact half-open month bounds are retained in period_start/period_end."
                        ),
                    ),
                    country_iso="GB",
                    geo_confidence=GeoConfidence.COUNTRY,
                    reliability=Reliability.F,
                    grade_rationale=(
                        "Official ONS statistical observation; methodology, revisions and "
                        "fitness for the research question remain unassessed."
                    ),
                )
            )
        if len(items) > MAX_MONTHS:
            raise ValueError("ONS result exceeds the selected interval")
        return sorted(items, key=publication_order)

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            language=self.language,
            temporal_scope=self.temporal_scope,
        )
