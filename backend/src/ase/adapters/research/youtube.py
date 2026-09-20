"""One aggregated, question-specific YouTube search through the official Data API v3.

This replaces the nine per-feed `research_social_*` providers that were retired with the
Reddit and YouTube feeds. It is one route, not a fan-out: a single `search.list` call
covers the whole platform for the requested dates, rather than one request per channel.

`search.list` is the expensive method in the API at 100 quota units, against a default
10,000 units a day. Scheduled channel polling already spends about 1,392 of those, so
this provider keeps its own rolling daily allowance and answers with a receipt instead
of a request once that allowance is spent. Nothing is collected without a key.

Only search result metadata is kept: title, publication time, channel identity, video
link and a bounded description excerpt. No transcript, caption track or media is fetched.
"""

from __future__ import annotations

import json
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.secret_urls import SecretFeedUrl
from ase.adapters.feeds.youtube import (
    API,
    MAX_EXCERPT,
    MAX_TITLE,
    ORIGIN,
    VIDEO_ID,
    WATCH,
    bounded_text,
    mapping_of,
    parsed_time,
    require_key,
)
from ase.adapters.research.feed import search_terms
from ase.adapters.research_records.records import receipt
from ase.application.ports import Clock
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery

SOURCE_ID = "research-youtube"
NAME = "YouTube video search"
MAX_RESULTS = 20
QUOTA_UNITS_PER_SEARCH = 100
# 40 searches a day is 4,000 units, which leaves the scheduled channel polls and their
# restart resolutions comfortably inside the default 10,000-unit daily project quota.
DAILY_SEARCH_ALLOWANCE = 40
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
LIMITATIONS = (
    "Platform-wide YouTube search result metadata, not a channel-curated or complete "
    "archive. At most 20 results from one request, ordered by upload date within the "
    "requested publication interval; YouTube decides relevance and coverage. Titles, "
    "channel labels and descriptions are uploader claims: a channel label does not "
    "authenticate an uploader, and no video, transcript, caption or comment is fetched. "
    "Upload time is not event time and search language is a hint, not detected language."
)


class YouTubeSearchResearchProvider:
    """Aggregated YouTube discovery. Present in the catalogue, silent without a key."""

    supports_planned_terms = True
    id = SOURCE_ID
    name = NAME
    language = "und"
    temporal_scope = (
        "Bounded search results filtered by upload date; the API does not guarantee a "
        "complete historical archive of the requested interval."
    )

    def __init__(self, http: FeedHttpClient, clock: Clock, api_key: str | None = None) -> None:
        self._http, self._clock = http, clock
        self._key = require_key(api_key) if api_key else None
        self.searches: deque[datetime] = deque()

    def __repr__(self) -> str:
        """Keep the configured key out of tracebacks, logs and test failure output."""
        return f"YouTubeSearchResearchProvider({self.id})"

    def supports(self, query: ResearchQuery) -> bool:
        return query.area is None and bool(search_terms(query))

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply bounded explicit phrases (maximum 1000 combined characters). "
                "Video search does not support area collection. No request was made.",
            )
        if self._key is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "A YouTube Data API key is not configured; no request was made. "
                "YouTube's robots.txt disallows the public channel feed path, so there "
                "is no unauthenticated alternative.",
            )
        now = self._clock.now()
        while self.searches and self.searches[0] <= now - timedelta(days=1):
            self.searches.popleft()
        if len(self.searches) >= DAILY_SEARCH_ALLOWANCE:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.BUDGET_EXHAUSTED,
                f"The local allowance of {DAILY_SEARCH_ALLOWANCE} video searches a day is "
                "spent; no request was made, so scheduled channel collection keeps its "
                "share of the project quota.",
            )
        self.searches.append(now)
        return await self._search(query, now)

    async def _search(self, query: ResearchQuery, now: datetime) -> ResearchBatch:
        try:
            payload = await self._fetch(self._url(query))
            items = self._parse(payload, query, now)
        except FeedFetchError:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "The YouTube Data API was unavailable, refused the configured key or "
                "returned an unusable response. No retry was made.",
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            LIMITATIONS,
            items,
        )

    def _url(self, query: ResearchQuery) -> SecretFeedUrl:
        phrases = "|".join(f'"{term}"' for term in search_terms(query))
        parameters = {
            "part": "snippet",
            "type": "video",
            "order": "date",
            "safeSearch": "none",
            "maxResults": str(MAX_RESULTS),
            "q": phrases,
            "publishedAfter": query.since.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "publishedBefore": query.until.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "key": self._key or "",
        }
        return SecretFeedUrl(ORIGIN, f"{API}/search?{urlencode(parameters)}")

    async def _fetch(self, target: SecretFeedUrl) -> dict[str, Any]:
        raw = await self._http.get_secret_bytes(target)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise FeedFetchError("YouTube response exceeds the collection byte limit.")
        try:
            payload = json.loads(raw)
        except (ValueError, RecursionError):
            raise FeedFetchError("YouTube returned an unusable response.") from None
        if not isinstance(payload, dict):
            raise FeedFetchError("YouTube returned an unusable response.")
        return payload

    def _parse(
        self, payload: dict[str, Any], query: ResearchQuery, now: datetime
    ) -> tuple[Event, ...]:
        rows = payload.get("items")
        events: dict[str, Event] = {}
        for row in rows if isinstance(rows, list) else []:
            event = self._to_event(mapping_of(row), now)
            when = event.published_at if event is not None else None
            # The half-open publication interval is enforced here, not trusted upstream.
            if event is not None and when is not None and query.since <= when < query.until:
                events.setdefault(event.id, event)
        return tuple(events.values())[:MAX_RESULTS]

    def _to_event(self, row: dict[str, Any], now: datetime) -> Event | None:
        video_id = mapping_of(row.get("id")).get("videoId")
        snippet = mapping_of(row.get("snippet"))
        title = bounded_text(snippet.get("title"), MAX_TITLE)
        if not isinstance(video_id, str) or not VIDEO_ID.fullmatch(video_id) or not title:
            return None
        excerpt = bounded_text(snippet.get("description"), MAX_EXCERPT)
        return Event(
            id=event_id(self.id, video_id),
            source_id=self.id,
            category=Category.SOCIAL,
            subtype="video",
            title=title,
            summary=excerpt or None,
            url=f"{WATCH}{video_id}",
            published_at=parsed_time(snippet.get("publishedAt"), now),
            observed_at=now,
            geo_confidence=GeoConfidence.NONE,
            country_iso=None,
            language="und",
            tags=frozenset({"youtube"}),
            severity=None,
            reliability=Reliability.F,
            credibility=Credibility.CANNOT_BE_JUDGED,
            grade_rationale="Platform search result; uploader and claims are unassessed",
            attributes=freeze_attributes(
                {
                    "original_account": bounded_text(snippet.get("channelTitle"), 120) or None,
                    "original_channel_id": bounded_text(snippet.get("channelId"), 40) or None,
                    "video_id": video_id,
                    "collection_source_id": self.id,
                    "collection_route": "YouTube Data API v3 search.list",
                    "provenance_status": "unverified",
                    "language_basis": "uploader metadata; not independently detected",
                }
            ),
            content_hash=content_hash(video_id, title[:200]),
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            language=self.language,
            supports_planned_terms=self.supports_planned_terms,
            temporal_scope=self.temporal_scope,
        )
