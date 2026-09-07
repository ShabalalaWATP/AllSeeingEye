"""Optional UK registry snapshots, with one authenticated request and no identity merging.

Official contracts:
https://developer.company-information.service.gov.uk/authentication
https://developer-specs.company-information.service.gov.uk/guides/rateLimiting
https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/search/search-companies
https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/company-profile/company-profile
"""

import re
from dataclasses import replace
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research_records.companies_house_client import (
    ORIGIN,
    CompaniesHouseClient,
)
from ase.adapters.research_records.records import MAX_RESULTS, receipt, record_event, text
from ase.adapters.research_records.registry_lookup import RegistryLookupCapability
from ase.application.ports import Clock
from ase.domain.events import Category, Event, Reliability
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

PUBLIC_ORIGIN = "https://find-and-update.company-information.service.gov.uk"
LIMITATIONS = (
    "Current Companies House register snapshot, not a historical view for the requested dates. "
    "Name results are identity candidates only; confirm the company number separately. "
    "Bare numbers can overlap other registries; use GB: or companies-house: for UK identifiers. "
    "At most 20 results; no pagination, filings, officers or ownership records were fetched. "
    "Registry inclusion does not independently verify filed assertions or current operations."
)


def company_number(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    number = value.strip().upper()
    if re.fullmatch(r"[0-9]{1,8}", number):
        return number.zfill(8)
    return (
        number
        if re.fullmatch(r"(?:[A-Z]{2}[0-9]{6}|R[0-9]{7}|[A-Z]{2}[0-9]{5}[A-Z])", number)
        else None
    )


def _subject_number(subject: str) -> str | None:
    for prefix in ("gb:", "companies-house:"):
        if subject.lower().startswith(prefix):
            return company_number(subject[len(prefix) :])
    return company_number(subject)


class CompaniesHouseProvider(RegistryLookupCapability):
    registry_namespaces = ("gb_company_number",)
    id = "research-companies-house"
    name = "Companies House"
    temporal_scope = (
        "Current registry snapshot, not historical-window evidence or complete history."
    )

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        api_key: str | None = None,
        *,
        client: CompaniesHouseClient | None = None,
    ) -> None:
        self._clock = clock
        self._client = client or CompaniesHouseClient(http, clock, api_key)
        self._requests = self._client.requests

    def supports(self, query: ResearchQuery) -> bool:
        subject = (query.subject or "").strip()
        return (
            query.focus is ResearchFocus.COMPANY
            and query.country_iso in {None, "GB"}
            and bool(subject)
            and not any(ord(char) < 32 for char in subject)
            and not re.fullmatch(r"CIK\s*:?\s*[0-9]+", subject, re.IGNORECASE)
            and not (
                subject.lower().startswith(("gb:", "companies-house:"))
                and _subject_number(subject) is None
            )
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply a company name or UK number, e.g. GB:01234567 or companies-house:01234567.",
            )
        identity = _subject_number((query.subject or "").strip())
        url = (
            f"{ORIGIN}/company/{identity}"
            if identity
            else f"{ORIGIN}/search/companies?"
            + urlencode({"q": (query.subject or "").strip(), "items_per_page": MAX_RESULTS})
        )
        return await self._client.collect(
            self.id, self.name, url, lambda payload: self._parse(payload, identity), LIMITATIONS
        )

    def _parse(self, payload: Any, identity: str | None) -> list[Event]:
        if not isinstance(payload, dict):
            raise ValueError("Invalid company response")
        rows: list[Any]
        if identity:
            if company_number(payload.get("company_number")) != identity:
                raise ValueError("Mismatched company profile")
            rows = [payload]
        else:
            raw_rows = payload.get("items")
            if not isinstance(raw_rows, list):
                raise ValueError("Invalid company search response")
            rows = raw_rows
        items: list[Event] = []
        seen: set[str] = set()
        for row in rows[:MAX_RESULTS]:
            if not isinstance(row, dict):
                continue
            number = company_number(row.get("company_number"))
            name = text(row.get("company_name" if identity else "title"), 200)
            if not number or not name or number in seen:
                continue
            seen.add(number)
            status = text(row.get("company_status"), 80) or "not supplied"
            formed = text(row.get("date_of_creation"), 32) or "not supplied"
            company_type = (
                text(row.get("type" if identity else "company_type"), 80) or "not supplied"
            )
            match = "requested_company_number" if identity else "candidate_only"
            event = record_event(
                self.id,
                number,
                f"{'Company profile' if identity else 'Company candidate'}: {name}",
                f"Companies House lists {name}, company number {number}, status {status}, "
                f"type {company_type}, reported incorporation date {formed}. "
                + (
                    "The response matches the requested registry number. "
                    if identity
                    else "This name candidate does not confirm the intended subject's identity. "
                )
                + "The register does not verify filed claims, ownership or current operations.",
                f"{PUBLIC_ORIGIN}/company/{number}",
                self._clock.now(),
                category=Category.ECONOMIC,
                attributes={
                    "company_number": number,
                    "company_name": name,
                    "company_status": status,
                    "company_type": company_type,
                    "reported_date_of_creation": formed,
                    "identity_match": match,
                    "record_kind": "current_registry_snapshot",
                    "record_issuer": "Companies House",
                    "timestamp_basis": "collection time; snapshot publication time unknown",
                },
            )
            items.append(
                replace(
                    event,
                    reliability=Reliability.F,
                    grade_rationale="Registry assertions and subject identity are unassessed.",
                )
            )
        if identity and not items:
            raise ValueError("Incomplete company profile")
        return items
