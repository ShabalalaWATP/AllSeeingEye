"""SEC JSON records by CIK and separate name candidates; no filing pages are scraped.

Endpoints and fair access: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
The injected guarded client must use the operator's identifying contact User-Agent.
"""

import asyncio
import re
from dataclasses import replace
from itertools import islice
from typing import Any

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.research_records.records import (
    MAX_RESULTS,
    collect_json,
    receipt,
    record_event,
    text,
)
from ase.adapters.research_records.registry_lookup import RegistryLookupCapability
from ase.adapters.research_records.sec_client import SecClient
from ase.adapters.research_records.sec_history import archives, index
from ase.application.ports import Clock
from ase.domain.events import Category, Event
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery
from ase.domain.sec_filing_time import filing_source_date
from ase.domain.sec_filings import parse_filing_date

DIRECTORY_URL = "https://www.sec.gov/files/company_tickers.json"


def cik(value: Any) -> str | None:
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(?:CIK\s*:?[ ]*)?([0-9]{1,10})", value.strip(), re.IGNORECASE)
    return match[1].zfill(10) if match and int(match[1]) else None


class SecSubmissionsProvider(RegistryLookupCapability):
    registry_namespaces = ("sec_cik",)
    temporal_scope = (
        "Filing metadata filtered by filing date, at most 20 records from recent and "
        "three declared older-history pages. Filing contents require explicit selection."
    )
    id = "research-sec-submissions"
    name = "SEC EDGAR submissions"

    def __init__(
        self, http: FeedHttpClient, clock: Clock, *, client: SecClient | None = None
    ) -> None:
        self._http, self._clock = http, clock
        self._sec = client or SecClient(http)

    def supports(self, query: ResearchQuery) -> bool:
        return query.focus is ResearchFocus.COMPANY and cik(query.subject) is not None

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        identity = cik(query.subject)
        if not self.supports(query) or identity is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply an explicit SEC CIK; names are not automatically resolved.",
            )
        items: list[Event] = []
        fetched, available = 0, 0
        try:
            self._sec.require_configured()
        except FeedFetchError as exc:
            return receipt(self.id, self.name, CollectionStatus.UNAVAILABLE, str(exc))
        try:
            async with asyncio.timeout(20):
                data = await index(self._sec, identity)
                items = self._parse(data, identity, query)
                names, truncated = archives(data, identity, query.since.date(), query.until.date())
                available = len(names)
                seen = {event.id for event in items}
                for name in names[:3]:
                    if len(items) >= MAX_RESULTS:
                        break
                    older = await self._sec.get_json(f"https://data.sec.gov/submissions/{name}")
                    fetched += 1
                    wrapped = {"cik": identity, "name": data["name"], "filings": {"recent": older}}
                    for event in self._parse(wrapped, identity, query):
                        if event.id not in seen:
                            seen.add(event.id)
                            items.append(event)
                    items = items[:MAX_RESULTS]
        except TimeoutError:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.TIMED_OUT,
                "SEC metadata deadline reached; returned metadata is partial.",
                items,
            )
        except (FeedFetchError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "SEC metadata response unavailable or invalid; no retry. Any "
                "returned rows are partial.",
                items,
            )
        note = (
            f"Filing metadata only; recent and {fetched} of {available} matching older pages read. "
            "At most 20 records; filing assertions are not SEC verification. "
            "Use explicit filing selection to import primary-document text."
            " Date filtering uses reported filing calendar days and possible day overlap, "
            "not known publication instants or a known source timezone."
        )
        if fetched < available or truncated:
            note += " History is incomplete; narrow the date interval or use the filing picker."
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            note,
            items,
        )

    def _parse(self, data: dict[str, Any], identity: str, query: ResearchQuery) -> list[Event]:
        if cik(data.get("cik")) != identity or not text(data.get("name")):
            raise ValueError("Mismatched company identity")
        filings = data.get("filings")
        recent = filings.get("recent") if isinstance(filings, dict) else None
        if not isinstance(recent, dict):
            raise ValueError("Missing submissions")
        columns: list[list[Any]] = []
        for key in ("accessionNumber", "filingDate", "form"):
            column = recent.get(key)
            if not isinstance(column, list):
                raise ValueError("Invalid submissions columns")
            columns.append(column)
        if len({len(column) for column in columns}) != 1:
            raise ValueError("Misaligned submissions columns")
        items: list[Event] = []
        seen: set[str] = set()
        for accession, filed, form in islice(zip(*columns, strict=True), 2000):
            if not isinstance(accession, str) or not re.fullmatch(
                r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession
            ):
                continue
            if accession in seen or not isinstance(filed, str) or not isinstance(form, str):
                continue
            try:
                filed_day = parse_filing_date(filed)
            except ValueError:
                continue
            if not query.since.date() <= filed_day <= query.until.date():
                continue
            seen.add(accession)
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(identity)}/"
                f"{accession.replace('-', '')}/{accession}-index.html"
            )
            items.append(
                record_event(
                    self.id,
                    f"{identity}:{accession}",
                    f"{text(data['name'], 180)}: SEC form {text(form, 32)}",
                    f"SEC records a form {text(form, 32)} filing dated {filed}, "
                    f"accession {accession}, for CIK {identity}. Metadata only; "
                    "filing contents and assertions were not verified. "
                    "The publication date has day precision.",
                    url,
                    self._clock.now(),
                    category=Category.ECONOMIC,
                    attributes={
                        "cik": identity,
                        "accession": accession,
                        "form": text(form, 32),
                        "filing_date": filed,
                        "date_precision": "day",
                        "record_kind": "filing_metadata",
                    },
                )
            )
            if len(items) == MAX_RESULTS:
                break
        # Day-level filing metadata is not a known UTC publication instant.
        return [
            replace(
                item,
                published_at=None,
                source_dates=(filing_source_date(str(item.attributes["filing_date"])),),
            )
            for item in items
        ]


class SecCompanyDirectoryProvider:
    temporal_scope = (
        "Current ticker-directory identity candidates; not a historical company directory."
    )
    id = "research-sec-company-directory"
    name = "SEC company identity candidates"

    def __init__(
        self, http: FeedHttpClient, clock: Clock, *, client: SecClient | None = None
    ) -> None:
        self._http, self._clock = client or SecClient(http), clock

    def supports(self, query: ResearchQuery) -> bool:
        return (
            query.focus is ResearchFocus.COMPANY
            and bool(query.subject and query.subject.strip())
            and cik(query.subject) is None
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply a company name or ticker for candidate matching.",
            )
        return await collect_json(
            self._http,
            self.id,
            self.name,
            DIRECTORY_URL,
            lambda data: self._parse(data, (query.subject or "").casefold().strip()),
            "Current SEC ticker-directory candidates, not verified identity matches or a "
            "complete company register. At most eight matches; historical names and filings "
            "were not fetched. Confirm an explicit CIK before filing collection.",
        )

    def _parse(self, data: dict[str, Any], subject: str) -> list[Event]:
        matches = []
        for value in islice(data.values(), 20000):
            if not isinstance(value, dict):
                continue
            identity = cik(value.get("cik_str"))
            name, ticker = text(value.get("title")), text(value.get("ticker"), 32)
            exact = subject in {name.casefold(), ticker.casefold()}
            if identity and name and (exact or (len(subject) >= 3 and subject in name.casefold())):
                matches.append((not exact, identity, name, ticker))
        items, seen = [], set()
        for _, identity, name, ticker in sorted(matches):
            if identity in seen:
                continue
            seen.add(identity)
            items.append(
                record_event(
                    self.id,
                    identity,
                    f"Company candidate: {name}",
                    f"Current SEC directory associates {name} with ticker {ticker} and CIK "
                    f"{identity}. This is a name/ticker candidate, not confirmation that it "
                    "is the intended subject; directory accuracy and coverage are not "
                    "guaranteed by SEC.",
                    f"https://www.sec.gov/edgar/browse/?CIK={identity}",
                    self._clock.now(),
                    category=Category.ECONOMIC,
                    attributes={
                        "cik": identity,
                        "ticker": ticker,
                        "identity_match": "candidate_only",
                        "record_kind": "current_directory_snapshot",
                    },
                )
            )
            if len(items) == 8:
                break
        return items


class CompaniesHouseUnavailableProvider:
    temporal_scope = "No collection capability configured; historical coverage is unavailable."
    """A receipt makes the missing credential integration explicit, without sending a key."""

    id = "research-companies-house"
    name = "Companies House"

    def supports(self, query: ResearchQuery) -> bool:
        return query.focus is ResearchFocus.COMPANY and query.country_iso == "GB"

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        return receipt(
            self.id,
            self.name,
            CollectionStatus.UNAVAILABLE if self.supports(query) else CollectionStatus.UNSUPPORTED,
            "Companies House requires a configured API key and host-bound per-request Basic "
            "authentication. This integration is unavailable; no request or credential was sent.",
        )
