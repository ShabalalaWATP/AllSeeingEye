"""Daily Russian-loss claims published by the General Staff of Ukraine, via a public mirror API.

Each day's cumulative figures become one event whose attributes hold the claim. They are a
belligerent's own statement: the source grade and the wording say so on every record.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from types import MappingProxyType
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.conflict_values import public_link, text
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
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
from ase.domain.ukraine.losses import (
    HEADLINE_CATEGORIES,
    LOSS_CATEGORIES,
    MAX_CLAIMS,
    ClaimedLosses,
    claim_attributes,
    parse_counts,
)

SERIES_DAYS = 90
# The mirror refuses limits above 50 (HTTP 422 since September 2026); offset pages the window.
PAGE_SIZE = 50
MAX_PAGES = -(-MAX_CLAIMS // PAGE_SIZE)
SPEC = SourceSpec(
    id="ukraine_general_staff",
    name="General Staff of Ukraine daily loss claims",
    organisation="General Staff of the Armed Forces of Ukraine (mirror: russianwarship.rip)",
    category=Category.CONFLICT,
    kind=SourceKind.API,
    url="https://russianwarship.rip/api/v2/statistics",
    reliability=Reliability.C,
    poll_interval=timedelta(hours=6),
    homepage="https://russianwarship.rip/",
    licence_note=(
        "Public mirror of the General Staff's daily summary; each record links the original "
        "post. Figures are the claimant's own and are shown as claims."
    ),
    flags=frozenset({"interested_party", "claimed_figures"}),
)


class GeneralStaffLossesConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    def _url(self, today: date, offset: int = 0) -> str:
        start = today - timedelta(days=SERIES_DAYS)
        query = urlencode(
            {
                "date_from": start.isoformat(),
                "date_to": today.isoformat(),
                "limit": PAGE_SIZE,
                "offset": offset,
            }
        )
        return f"{self.spec.url}?{query}"

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        try:
            records = await self._records(now.date())
        except NotModified:
            return []
        events: dict[str, Event] = {}
        for row in records:
            claim = parse_claim(row)
            if claim is not None:
                event = self._to_event(claim, now)
                events[event.id] = event
        return list(events.values())

    async def _records(self, today: date) -> list[Any]:
        """Offset pages of at most PAGE_SIZE rows until a short page, within MAX_CLAIMS."""
        rows: list[Any] = []
        for page in range(MAX_PAGES):
            payload = await self._http.get_json(
                self._url(today, page * PAGE_SIZE), conditional=False
            )
            data = payload.get("data") if isinstance(payload, dict) else None
            records = data.get("records") if isinstance(data, dict) else None
            if not isinstance(records, list):
                raise FeedFetchError("General Staff mirror returned an invalid envelope.")
            if len(records) > PAGE_SIZE:
                raise FeedFetchError("General Staff mirror returned more records than requested.")
            rows.extend(records)
            if len(records) < PAGE_SIZE:
                break
        return rows

    def _to_event(self, claim: ClaimedLosses, now: datetime) -> Event:
        headline = ", ".join(
            f"{LOSS_CATEGORIES[key].lower()} {claim.totals[key]:,}"
            for key in HEADLINE_CATEGORIES
            if key in claim.totals
        )
        reported = datetime.combine(claim.reported_on, datetime.min.time(), tzinfo=now.tzinfo)
        return Event(
            id=event_id(self.spec.id, claim.reported_on.isoformat()),
            source_id=self.spec.id,
            category=Category.CONFLICT,
            subtype="claimed_losses",
            title=f"General Staff of Ukraine claims cumulative Russian losses, day {claim.day}",
            summary=(
                f"Claimed totals on {claim.reported_on.isoformat()}: {headline}. "
                "A belligerent's own figures, not independently verified."
            )[:500],
            url=claim.source_url,
            published_at=reported,
            observed_at=now,
            country_iso="UA",
            reliability=self.spec.reliability,
            credibility=Credibility.CANNOT_BE_JUDGED,
            grade_rationale="Interested party's claim; no independent count is available.",
            tags=frozenset({"official", "claimed", "interested_party"}),
            attributes=freeze_attributes(claim_attributes(claim)),
            content_hash=content_hash(
                claim.reported_on.isoformat(), *(str(v) for v in claim.totals.values())
            ),
        )


def parse_claim(row: Any) -> ClaimedLosses | None:
    """One mirror record: report date, war day, original post link, totals and increase."""
    if not isinstance(row, dict):
        return None
    try:
        reported_on = date.fromisoformat(text(row.get("date"), 10))
    except ValueError:
        return None
    day = row.get("day")
    totals = parse_counts(row.get("stats"))
    if not isinstance(day, int) or isinstance(day, bool) or day <= 0 or not totals:
        return None
    return ClaimedLosses(
        reported_on=reported_on,
        day=day,
        source_url=public_link(row.get("resource")),
        totals=MappingProxyType(totals),
        increase=MappingProxyType(parse_counts(row.get("increase"))),
    )
