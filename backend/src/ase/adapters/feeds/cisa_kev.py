"""CISA Known Exploited Vulnerabilities catalogue (CC0), recent additions only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import (
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
)

RECENT_DAYS = 30


def _first_url(notes: object) -> str | None:
    if not isinstance(notes, str):
        return None
    for part in notes.split(";"):
        candidate = part.strip()
        if candidate.startswith("http"):
            return candidate.split(" ")[0]
    return None


class CisaKevConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        now = self._clock.now()
        cutoff = now - timedelta(days=RECENT_DAYS)
        items = data.get("vulnerabilities", []) if isinstance(data, dict) else []
        events = []
        for item in items:
            event = self._to_event(item, now)
            if event is not None and event.published_at >= cutoff:
                events.append(event)
        return events

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
                }
            ),
            content_hash=content_hash(cve, str(item.get("dueDate")), ransomware, name),
        )
