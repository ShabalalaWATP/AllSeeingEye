"""Reviewed YouTube channels read through the official Data API v3.

`https://www.youtube.com/robots.txt` disallows `/feeds/videos.xml`, the channel Atom
path this application used to poll, so the API is the only compliant route and it
needs an operator key. Without `ASE_YOUTUBE_API_KEY` no connector is built at all.

The cheap call pattern is deliberate. `search.list` costs 100 quota units; resolving a
channel's uploads playlist once with `channels.list` costs 1, and every later poll is a
`playlistItems.list` call that also costs 1. Twenty-nine channels polled every thirty
minutes therefore spend about 1,392 units a day against the default 10,000, plus one
unit per channel after a restart.

Only the title, publication time, channel identity, video link and a bounded excerpt of
the description are kept. No transcript, caption track, comment or media is fetched.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.secret_urls import SecretFeedUrl
from ase.adapters.feeds.youtube_channels import UPLOADS_ID, YouTubeChannel
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Event,
    GeoConfidence,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

ORIGIN = "https://www.googleapis.com"
API = f"{ORIGIN}/youtube/v3"
WATCH = "https://www.youtube.com/watch?v="
MAX_ITEMS = 25
MAX_TITLE = 300
MAX_EXCERPT = 500
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_KEY = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
LICENCE_NOTE = "YouTube Data API v3 terms; titles, links and a bounded excerpt only"


def require_key(value: str) -> str:
    if not _KEY.fullmatch(value):
        raise ValueError("Invalid YouTube Data API key format")
    return value


def spec_for(channel: YouTubeChannel) -> SourceSpec:
    return SourceSpec(
        id=channel.source_id,
        name=f"{channel.name} (YouTube)",
        organisation=channel.organisation,
        category=Category.SOCIAL,
        kind=SourceKind.API,
        url=f"{API}/playlistItems",
        reliability=channel.reliability,
        poll_interval=timedelta(minutes=channel.minutes),
        requires_key=True,
        language=channel.language,
        licence_note=LICENCE_NOTE,
        homepage=f"https://www.youtube.com/{channel.handle}",
        flags=frozenset({"state_controlled"}) if channel.state_aligned else frozenset(),
    )


def bounded_text(value: object, limit: int) -> str:
    return " ".join(str(value).split())[:limit] if isinstance(value, str) else ""


def parsed_time(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


def mapping_of(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class YouTubeChannelConnector:
    """One reviewed channel. The key never leaves this object or its secret URLs."""

    def __init__(
        self, http: FeedHttpClient, clock: Clock, key: str, channel: YouTubeChannel
    ) -> None:
        self.spec = spec_for(channel)
        self._http, self._clock, self._channel = http, clock, channel
        selector = (
            f"id={channel.channel_id}"
            if channel.channel_id
            else f"forHandle={channel.handle.lstrip('@')}"
        )
        self._resolve = SecretFeedUrl(
            ORIGIN, f"{API}/channels?part=contentDetails&{selector}&key={require_key(key)}"
        )
        self._items = (
            f"{API}/playlistItems?part=snippet,contentDetails"
            f"&maxResults={MAX_ITEMS}&key={key}&playlistId="
        )
        self._uploads = ""

    def __repr__(self) -> str:
        """Keep the configured key out of tracebacks, logs and test failure output."""
        return f"YouTubeChannelConnector({self.spec.id})"

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        if not self._uploads:
            self._uploads = await self._uploads_playlist()
        payload = await self._json(SecretFeedUrl(ORIGIN, self._items + self._uploads))
        rows = payload.get("items")
        items = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        events: dict[str, Event] = {}
        for row in items[:MAX_ITEMS]:
            event = self._to_event(row, now)
            if event is not None:
                events.setdefault(event.id, event)
        return list(events.values())

    async def _uploads_playlist(self) -> str:
        """One 1-unit call resolves the handle and the uploads playlist together."""
        payload = await self._json(self._resolve)
        rows = payload.get("items")
        first = mapping_of(rows[0]) if isinstance(rows, list) and rows else {}
        related = mapping_of(mapping_of(first.get("contentDetails")).get("relatedPlaylists"))
        uploads = related.get("uploads")
        if not isinstance(uploads, str) or not UPLOADS_ID.fullmatch(uploads):
            raise FeedFetchError("YouTube did not return an uploads playlist for this channel.")
        return uploads

    async def _json(self, target: SecretFeedUrl) -> dict[str, Any]:
        payload = await self._http.get_secret_bytes(target)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise FeedFetchError("YouTube response exceeds the collection byte limit.")
        try:
            data = json.loads(payload)
        except (ValueError, RecursionError):
            raise FeedFetchError("YouTube returned an unusable response.") from None
        if not isinstance(data, dict):
            raise FeedFetchError("YouTube returned an unusable response.")
        return data

    def _to_event(self, row: dict[str, Any], now: datetime) -> Event | None:
        snippet = mapping_of(row.get("snippet"))
        video_id = mapping_of(snippet.get("resourceId")).get("videoId")
        title = bounded_text(snippet.get("title"), MAX_TITLE)
        if not isinstance(video_id, str) or not VIDEO_ID.fullmatch(video_id) or not title:
            return None
        if title in {"Private video", "Deleted video"}:
            return None
        published = mapping_of(row.get("contentDetails")).get("videoPublishedAt")
        excerpt = bounded_text(snippet.get("description"), MAX_EXCERPT)
        channel = self._channel
        return Event(
            id=event_id(self.spec.id, video_id),
            source_id=self.spec.id,
            category=Category.SOCIAL,
            subtype="video",
            title=title,
            summary=excerpt or None,
            url=f"{WATCH}{video_id}",
            published_at=parsed_time(published or snippet.get("publishedAt"), now),
            observed_at=now,
            geo_confidence=GeoConfidence.NONE,
            country_iso=None,
            language=channel.language,
            tags=channel.tags,
            severity=None,
            reliability=channel.reliability,
            credibility=channel.credibility,
            grade_rationale=channel.rationale,
            attributes=freeze_attributes(
                {
                    "instance": channel.name,
                    "channel": channel.name,
                    "channel_handle": channel.handle,
                    "channel_id": (
                        bounded_text(snippet.get("channelId"), 40) or channel.channel_id or None
                    ),
                    "organisation": channel.organisation,
                    "topics": ", ".join(channel.topics),
                    "video_id": video_id,
                    "collection_route": "YouTube Data API v3 playlistItems.list",
                }
            ),
            content_hash=content_hash(video_id, title[:200]),
        )
