"""Explicit single-country annual indicator queries, never inferred from prose.

https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures
https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

import asyncio
import math
import re
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.adapters.research_records.records import receipt, text
from ase.adapters.research_subjects.events import subject_event as record_event
from ase.application.ports import Clock
from ase.domain.events import Category, Event
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery


def indicator_subject(value: str | None) -> tuple[str, str, int, int] | None:
    match = re.fullmatch(
        r"WB:([A-Za-z]{2}):([A-Z][A-Z0-9_.]{1,79}):([0-9]{4}):([0-9]{4})", value or ""
    )
    if not match:
        return None
    country, indicator, first, last = match.groups()
    start, end = int(first), int(last)
    return (
        (country.upper(), indicator, start, end)
        if 1900 <= start <= end <= 2100 and end - start < 20
        else None
    )


class WorldBankProvider:
    id = "research-world-bank"
    name = "World Bank annual indicators"
    temporal_scope = (
        "Current snapshot of an explicit annual series (at most 20 years); not historical vintages."
    )

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self.http, self.clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        parsed = indicator_subject(query.subject)
        return bool(
            query.focus is ResearchFocus.GENERAL
            and parsed
            and (query.country_iso is None or query.country_iso.upper() == parsed[0])
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        subject = indicator_subject(query.subject)
        if subject is None or not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply WB:GB:NY.GDP.MKTP.CD:2020:2024 with one country and at most "
                "20 annual periods; country filters must agree.",
            )
        country, indicator, start, end = subject
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?" + urlencode(
            {
                "format": "json",
                "date": f"{start}:{end}",
                "per_page": 20,
                "page": 1,
            }
        )
        try:
            async with asyncio.timeout(20):
                data = await self.http.get_json(url, conditional=False, max_redirects=0)
            items = self.parse(data, subject)
        except TimeoutError:
            return receipt(
                self.id, self.name, CollectionStatus.TIMED_OUT, "Indicator request timed out."
            )
        except (FeedFetchError, NotModified, ValueError, TypeError, KeyError, OverflowError):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "Indicator service was unavailable or returned unusable data. No retry was made.",
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            "Current snapshot of the explicit annual series, not a historical data vintage. "
            "Event time is collection time; observation years are recorded separately. "
            "Null observations are retained as missing, not zero. No interpolation, "
            "unit inference or additional pages; at most 20 periods.",
            items,
        )

    def parse(self, data: Any, subject: tuple[str, str, int, int]) -> list[Event]:
        if not isinstance(data, list) or len(data) != 2 or not isinstance(data[0], dict):
            raise ValueError("Invalid indicator response")
        rows = data[1]
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise ValueError("Invalid indicator rows")
        country, indicator, start, end = subject
        result, seen = [], set()
        for row in rows[:20]:
            if not isinstance(row, dict):
                continue
            source_country, source_indicator = row.get("country"), row.get("indicator")
            if not (
                isinstance(source_country, dict)
                and source_country.get("id") == country
                and isinstance(source_indicator, dict)
                and source_indicator.get("id") == indicator
            ):
                continue
            period = row.get("date")
            if not isinstance(period, str) or not re.fullmatch(r"[0-9]{4}", period):
                continue
            if not start <= int(period) <= end or period in seen:
                continue
            value = row.get("value")
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                continue
            seen.add(period)
            name, unit = text(source_indicator.get("value"), 180), text(row.get("unit"), 80)
            result.append(
                record_event(
                    self.id,
                    f"{country}:{indicator}:{period}",
                    f"{country}: {name or indicator} ({period})",
                    f"World Bank indicator {indicator}, country {country}, "
                    f"observation year {period}. "
                    f"Value: {value if value is not None else 'missing'}. "
                    f"Unit as supplied: {unit or 'not recorded'}. "
                    "Current snapshot, not a historical release vintage. "
                    "Units and missing values must not be inferred.",
                    f"https://data.worldbank.org/indicator/{indicator}?locations={country}",
                    self.clock.now(),
                    category=Category.ECONOMIC,
                    attributes={
                        "record_kind": "annual_indicator_snapshot",
                        "indicator": indicator,
                        "observation_year": period,
                        "country_code": country,
                        "value": value,
                        "unit": unit or None,
                        "missing_value": value is None,
                        "last_updated": text(data[0].get("lastupdated"), 32) or None,
                    },
                ).with_changes(country_iso=country)
            )
        return result
