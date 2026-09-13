"""ISW's daily Russian Offensive Campaign Assessment through the site's WordPress JSON index.

The RSS endpoints refuse automated readers, so the public posts index is read instead. Only
the title, link, date and a short plain-text excerpt are kept, with attribution to ISW.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.conflict_values import public_link, text, when
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Reliability,
    content_hash,
    event_id,
)
from ase.domain.sources import SourceKind, SourceSpec

MAX_POSTS = 10
MAX_EXCERPT = 400
SEARCH = "Russian Offensive Campaign Assessment"
SPEC = SourceSpec(
    id="isw_assessments",
    name="ISW Russian Offensive Campaign Assessments",
    organisation="Institute for the Study of War",
    category=Category.CONFLICT,
    kind=SourceKind.API,
    url="https://www.understandingwar.org/wp-json/wp/v2/posts",
    reliability=Reliability.B,
    poll_interval=timedelta(hours=1),
    homepage="https://www.understandingwar.org/",
    licence_note=(
        "ISW fair use and attribution policy: title, link, date and a short excerpt only, "
        "credited to the Institute for the Study of War."
    ),
    flags=frozenset({"assessment", "context_reporting"}),
)
_TAGS = re.compile(r"<[^>]+>")


def plain(value: Any, limit: int) -> str:
    """Rendered WordPress fields carry HTML; keep unescaped text only."""
    return " ".join(html.unescape(_TAGS.sub(" ", text(value, 4_000))).split())[:limit]


class IswAssessmentsConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock
        query = urlencode(
            {
                "search": SEARCH,
                "per_page": MAX_POSTS,
                "_fields": "id,date_gmt,link,title,excerpt",
            }
        )
        self._url = f"{self.spec.url}?{query}"

    async def fetch(self) -> list[Event]:
        try:
            payload = await self._http.get_json(self._url)
        except NotModified:
            return []
        if not isinstance(payload, list):
            raise FeedFetchError("ISW returned an invalid posts index.")
        if len(payload) > MAX_POSTS:
            raise FeedFetchError("ISW returned more posts than requested.")
        now = self._clock.now()
        events: dict[str, Event] = {}
        for row in payload:
            if isinstance(row, dict) and (event := self._to_event(row, now)):
                events[event.id] = event
        return list(events.values())

    def _to_event(self, row: dict[str, Any], now: datetime) -> Event | None:
        post_id = text(row.get("id"), 20)
        title = plain((row.get("title") or {}).get("rendered"), 300)
        link = public_link(row.get("link"))
        if not post_id or not title or link is None or SEARCH.lower() not in title.lower():
            return None
        published = when(text(row.get("date_gmt"), 40) + "Z") if row.get("date_gmt") else None
        excerpt = plain((row.get("excerpt") or {}).get("rendered"), MAX_EXCERPT)
        return Event(
            id=event_id(self.spec.id, post_id),
            source_id=self.spec.id,
            category=Category.CONFLICT,
            subtype="assessment",
            title=title,
            summary=(excerpt or "Daily assessment published by ISW.")
            + " Assessment by a named research institute, not a verified record.",
            url=link,
            published_at=published,
            observed_at=now,
            country_iso="UA",
            geo_confidence=GeoConfidence.COUNTRY,
            reliability=self.spec.reliability,
            credibility=Credibility.POSSIBLY_TRUE,
            grade_rationale="Named institute's daily assessment; conclusions are its own.",
            tags=frozenset({"assessment"}),
            content_hash=content_hash(title, excerpt, link),
        )
