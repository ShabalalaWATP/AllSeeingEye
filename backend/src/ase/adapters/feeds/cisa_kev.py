"""CISA Known Exploited Vulnerabilities catalogue (CC0), recent additions only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import monotonic
from typing import Any

from ase.adapters.feeds.base import HttpFeed
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.adapters.feeds.http_contracts import FeedHttpStatusError
from ase.adapters.feeds.kev_scores import KevScoreEnrichment
from ase.application.feeds.pipeline import clean_text
from ase.application.ports import Clock
from ase.domain.events import (
    MAX_ATTRIBUTE_CHARS,
    Category,
    Credibility,
    Event,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

SPEC = SourceSpec(
    id="cisa_kev",
    name="CISA Known Exploited Vulnerabilities",
    organisation="Cybersecurity and Infrastructure Security Agency",
    category=Category.CYBER,
    kind=SourceKind.API,
    url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
    reliability=Reliability.A,
    poll_interval=timedelta(hours=1),
    licence_note="CC0 1.0",
    homepage="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
    flags=frozenset({"authoritative"}),
)

RECENT_DAYS = 30
# CISA-maintained distribution of the same CC0 catalogue, not a third-party proxy.
OFFICIAL_MIRROR = (
    "https://raw.githubusercontent.com/cisagov/kev-data/"
    "develop/known_exploited_vulnerabilities.json"
)


def _first_url(notes: object) -> str | None:
    if not isinstance(notes, str):
        return None
    for part in notes.split(";"):
        candidate = part.strip()
        if candidate.startswith(("https://", "http://")):
            return candidate.split(" ")[0]
    return None


class CisaKevConnector(HttpFeed):
    spec = SPEC

    def __init__(
        self, http: FeedHttpClient, clock: Clock, scores: KevScoreEnrichment | None = None
    ) -> None:
        super().__init__(http, clock)
        self._scores = scores
        self._recent: list[Event] = []

    async def fetch(self) -> list[Event]:
        started = monotonic()
        try:
            data = await self._catalogue()
        except NotModified:
            if self._scores is None:
                return []
            cutoff = self._clock.now() - timedelta(days=RECENT_DAYS)
            recent = [
                event
                for event in self._recent
                if event.published_at and event.published_at >= cutoff
            ]
            return await self._enrich(recent, started)
        now = self._clock.now()
        cutoff = now - timedelta(days=RECENT_DAYS)
        if not isinstance(data, dict) or not isinstance(data.get("vulnerabilities"), list):
            raise FeedFetchError("CISA KEV response does not contain a vulnerability catalogue")
        items = data["vulnerabilities"]
        events = []
        for item in items:
            event = self._to_event(item, now) if isinstance(item, dict) else None
            if (
                event is not None
                and event.published_at is not None
                and cutoff <= event.published_at <= now
            ):
                events.append(event)
        if self._scores is not None:
            self._recent = events[:1000]
            return await self._enrich(events, started)
        return events

    async def _enrich(self, events: list[Event], started: float) -> list[Event]:
        if self._scores is None:
            return events
        # The scheduler's normal KEV fetch allowance is 60 seconds. Leave five
        # seconds for release after a slow catalogue, and never extend that budget.
        remaining = max(0.0, 55 - (monotonic() - started))
        return await self._scores.enrich(events, available_seconds=remaining)

    async def _catalogue(self) -> Any:
        try:
            return await self._http.get_json(self.spec.url)
        except FeedHttpStatusError as exc:
            if exc.status_code != 403:
                raise
        # Both requests retain the shared client's DNS, size and timeout guards.
        return await self._http.get_json(OFFICIAL_MIRROR)

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        cve = str(item.get("cveID") or "")
        added = item.get("dateAdded")
        if not cve or not isinstance(added, str):
            return None
        try:
            published = datetime.strptime(added, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            return None
        ransomware = str(item.get("knownRansomwareCampaignUse") or "Unknown")
        name = str(item.get("vulnerabilityName") or "Known exploited vulnerability")
        raw_action = item.get("requiredAction")
        required_action = raw_action if isinstance(raw_action, str) else ""
        return Event(
            id=event_id(self.spec.id, cve),
            source_id=self.spec.id,
            category=Category.CYBER,
            subtype="known_exploited_vulnerability",
            title=f"{cve}: {name}",
            summary=str(item.get("shortDescription") or ""),
            url=_first_url(item.get("notes")) or self.spec.homepage,
            published_at=published,
            observed_at=now,
            tags=frozenset({"vulnerability", "kev"}),
            severity=0.7 if ransomware.lower() == "known" else 0.5,
            reliability=self.spec.reliability,
            credibility=Credibility.CONFIRMED,
            grade_rationale="Listed by CISA as exploited in the wild",
            attributes=freeze_attributes(
                {
                    "cve": cve,
                    "vendor": str(item.get("vendorProject") or ""),
                    "product": str(item.get("product") or ""),
                    "due_date": str(item.get("dueDate") or ""),
                    "ransomware": ransomware,
                    "cwes": ", ".join(str(c) for c in item.get("cwes") or []),
                    "required_action": clean_text(required_action, MAX_ATTRIBUTE_CHARS) or "",
                }
            ),
            content_hash=content_hash(
                cve, str(item.get("dueDate")), ransomware, name, required_action
            ),
        )
