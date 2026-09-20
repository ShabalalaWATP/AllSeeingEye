"""One public OCDS publication page, locally matched without a completeness claim.

https://www.contractsfinder.service.gov.uk/apidocumentation/Notices/1/GET-Published-Notice-OCDS-Search
The documented endpoint filters publication dates/stages, not company names.
"""

import asyncio
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research.feed import search_terms
from ase.adapters.research_records.record_metadata import bounded_json
from ase.adapters.research_records.records import (
    MAX_RESULTS,
    collect_json,
    receipt,
    record_event,
    text,
)
from ase.application.ports import Clock
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.events import Category, Event, Reliability
from ase.domain.languages import matching_text
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

ORIGIN = "https://www.contractsfinder.service.gov.uk"
LIMITATIONS = (
    "One Contracts Finder OCDS publication page, at most 20 releases, locally matched to supplied "
    "phrases. The API does not filter company names; no further pages or documents were fetched. "
    "This is not a complete procurement search or award history. Publication/edit dates are not "
    "contract performance dates. Names are candidates, not verified legal-entity matches; "
    "a notice is not proof of award fulfilment or misconduct."
)


class ContractsFinderProvider:
    supports_planned_terms = True

    id = "research-contracts-finder"
    name = "Contracts Finder publication notices"
    temporal_scope = (
        "Requested release-publication interval; first page only, not complete history."
    )

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock
        self._blocked_until: datetime | None = None
        self._lock = asyncio.Lock()

    def supports(self, query: ResearchQuery) -> bool:
        return (
            query.focus in {ResearchFocus.GENERAL, ResearchFocus.COMPANY}
            and (not query.country_isos or "GB" in query.country_isos)
            and bool(search_terms(query))
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply bounded explicit phrases for UK procurement notices.",
            )
        async with self._lock:
            if self._blocked_until and self._clock.now() < self._blocked_until:
                return receipt(
                    self.id,
                    self.name,
                    CollectionStatus.BUDGET_EXHAUSTED,
                    "Contracts Finder is in a five-minute failure cooldown; no request was made.",
                )
            url = (
                ORIGIN
                + "/Published/Notices/OCDS/Search?"
                + urlencode(
                    {
                        "publishedFrom": query.since.astimezone(UTC).isoformat(),
                        "publishedTo": query.until.astimezone(UTC).isoformat(),
                        "limit": MAX_RESULTS,
                    }
                )
            )
            result = await collect_json(
                self._http,
                self.id,
                self.name,
                url,
                lambda payload: self._parse(payload, query),
                LIMITATIONS,
            )
            # The guarded client intentionally hides HTTP response details. Waiting
            # after every failure also honours this API's documented 403 cooldown.
            if result.attempts[0].status in {CollectionStatus.FAILED, CollectionStatus.TIMED_OUT}:
                self._blocked_until = self._clock.now() + timedelta(minutes=5)
            return result

    def _parse(self, payload: dict[str, Any], query: ResearchQuery) -> list[Event]:
        releases = payload.get("releases")
        if not isinstance(releases, list):
            raise ValueError("Invalid OCDS release package")
        terms = tuple(matching_text(term, "en") for term in search_terms(query))
        events: list[Event] = []
        seen: set[str] = set()
        for release in releases[:MAX_RESULTS]:
            if not isinstance(release, dict):
                continue
            identity, ocid = text(release.get("id"), 300), text(release.get("ocid"), 200)
            if (
                not re.fullmatch(r"[A-Za-z0-9_-]{1,300}", identity)
                or not re.fullmatch(r"ocds-[A-Za-z0-9_-]{1,190}", ocid)
                or identity in seen
            ):
                continue
            try:
                published = datetime.fromisoformat(
                    str(release.get("date", "")).replace("Z", "+00:00")
                )
            except ValueError:
                continue
            if published.utcoffset() is None or not query.since <= published < query.until:
                continue
            tender = release.get("tender", {})
            buyer = release.get("buyer", {})
            if not isinstance(tender, dict) or not isinstance(buyer, dict):
                continue
            title = text(tender.get("title"), 250)
            description = text(tender.get("description"), 1000)
            buyer_name = text(buyer.get("name"), 200)
            awards = release.get("awards", [])
            suppliers: list[str] = []
            if isinstance(awards, list):
                for award in awards[:20]:
                    if not isinstance(award, dict) or not isinstance(award.get("suppliers"), list):
                        continue
                    suppliers.extend(
                        text(item.get("name"), 200)
                        for item in award["suppliers"][:20]
                        if isinstance(item, dict)
                    )
            suppliers = list(dict.fromkeys(suppliers))[:20]
            suppliers_json, suppliers_omitted = bounded_json(suppliers)
            haystack = matching_text(" ".join((title, description, buyer_name, *suppliers)), "en")
            if not title or not any(term in haystack for term in terms):
                continue
            seen.add(identity)
            event = record_event(
                self.id,
                identity,
                f"Procurement notice: {title}",
                f"Contracts Finder publication by {buyer_name or 'unspecified buyer'}. "
                f"Named suppliers: {', '.join(suppliers) or 'not supplied'}. {description} "
                "Names remain candidates; publication does not verify performance or misconduct.",
                f"{ORIGIN}/Published/OCDS/Record/{ocid}",
                self._clock.now(),
                category=Category.ECONOMIC,
                published=published,
                attributes={
                    "ocid": ocid,
                    "release_id": identity,
                    "reported_buyer": buyer_name,
                    "reported_suppliers": suppliers_json,
                    "reported_suppliers_omitted": suppliers_omitted,
                    "reported_tender_status": text(tender.get("status"), 80),
                    "package_published_date": text(payload.get("publishedDate"), 40),
                    "declared_licence": text(payload.get("license"), 250),
                    "identity_match": "phrase_candidate_only",
                    "record_issuer": "Contracts Finder",
                    "record_kind": "procurement_publication",
                    "timestamp_basis": "OCDS release publication/edit date",
                },
            )
            events.append(
                replace(
                    event,
                    reliability=Reliability.F,
                    grade_rationale="Notice assertions and subject identity remain unassessed.",
                )
            )
        return events

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_planned_terms=self.supports_planned_terms,
            temporal_scope=self.temporal_scope,
        )
