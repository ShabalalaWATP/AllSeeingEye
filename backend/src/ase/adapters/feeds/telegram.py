"""Curated public Telegram channels, read through the channel web preview page.

Most Ukraine and Russia war material breaks on Telegram first, and Telegram publishes
no read API for public channels without an account. The public web preview at
``https://t.me/s/<channel>`` is the only route, so this connector is deliberately narrow:
it requests that one page and nothing else, never media, never a link found in a post.

Grading is the point of the feature. Channels run by belligerents, state media and war
correspondents are participants in the events they describe, so every post sits at
doctrine's floor (reliability E, credibility 6) and carries the registry's viewpoint tags
so the interface marks state-aligned and official-issuer material exactly as it marks
state-aligned news feeds. Text excerpts and links only are collected; graphic imagery is
never fetched or stored.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ase.adapters.feeds.http import (
    FeedHttpClient,
    FeedHttpStatusError,
    NotModified,
)
from ase.adapters.feeds.telegram_channels import TelegramChannel, channel_url, preview_url
from ase.adapters.feeds.telegram_preview import (
    MAX_EXCERPT_CHARS,
    TelegramMarkupError,
    TelegramPost,
    parse_channel_preview,
)
from ase.application.ports import Clock
from ase.application.ports.feed_diagnostics import FeedBlocked
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
from ase.domain.sources import SourceKind, SourceSpec

UNAVAILABLE_RECHECK = timedelta(hours=6)
REFUSED_RECHECK = timedelta(hours=12)
TITLE_CHARS = 140
LICENCE_NOTE = (
    "Telegram terms; public channel web preview only. Text excerpts, timestamps and post "
    "links; no media, no account, no private or subscriber-only content."
)
GRADE_RATIONALE = (
    "Public Telegram post from a channel that is a party to, or aligned with, what it "
    "describes; neither the channel nor the claim is independently assessed."
)
# Fixed, operator-facing text: no URL, response body or upstream wording is ever included.
REFUSED_REASON = (
    "Telegram refused this application's request for the public channel preview. The "
    "application will not imitate a browser or sign in; it rechecks every 12 hours."
)


def channel_spec(channel: TelegramChannel) -> SourceSpec:
    return SourceSpec(
        id=channel.source_id,
        name=f"{channel.name} (Telegram)",
        organisation=channel.operator,
        category=Category.SOCIAL,
        kind=SourceKind.API,
        url=preview_url(channel.username),
        reliability=Reliability.E,
        poll_interval=timedelta(minutes=channel.poll_minutes),
        licence_note=LICENCE_NOTE,
        homepage=channel_url(channel.username),
        language=channel.language,
    )


def _title(text: str) -> str:
    first = text.split(". ", maxsplit=1)[0].strip()
    candidate = first if 20 <= len(first) <= TITLE_CHARS else text
    return candidate if len(candidate) <= TITLE_CHARS else candidate[: TITLE_CHARS - 1] + "…"


class TelegramChannelConnector:
    """One curated channel. A markup change stops collection instead of inventing posts."""

    def __init__(self, http: FeedHttpClient, clock: Clock, channel: TelegramChannel) -> None:
        self.spec = channel_spec(channel)
        self._http = http
        self._clock = clock
        self._channel = channel

    async def fetch(self) -> list[Event]:
        try:
            document = await self._http.get_text(self.spec.url)
        except NotModified:
            return []
        except FeedHttpStatusError as exc:
            # 429 is FeedRateLimitedError; the scheduler backs off and honours Retry-After.
            if exc.status_code in (401, 403, 404, 410, 451):
                raise FeedBlocked(REFUSED_REASON, self._clock.now() + REFUSED_RECHECK) from None
            raise
        try:
            preview = parse_channel_preview(document, self._channel.username)
        except TelegramMarkupError as exc:
            raise FeedBlocked(
                f"Telegram channel @{self._channel.username} is not collecting: {exc}. "
                "Posts are never guessed from an unrecognised page; rechecked every 6 hours.",
                self._clock.now() + UNAVAILABLE_RECHECK,
            ) from None
        now = self._clock.now()
        return [self._to_event(post, preview.title, now) for post in preview.posts]

    def _to_event(self, post: TelegramPost, title: str | None, now: datetime) -> Event:
        channel = self._channel
        return Event(
            id=event_id(self.spec.id, post.key),
            source_id=self.spec.id,
            category=Category.SOCIAL,
            subtype="post",
            title=_title(post.text),
            summary=post.text[:MAX_EXCERPT_CHARS],
            url=post.url,
            published_at=post.published_at,
            observed_at=now,
            geo_confidence=GeoConfidence.NONE,
            country_iso=None,
            language=channel.language,
            tags=frozenset({"telegram", channel.topic, *channel.viewpoint_tags}),
            severity=None,
            reliability=self.spec.reliability,
            credibility=Credibility.CANNOT_BE_JUDGED,
            grade_rationale=GRADE_RATIONALE,
            attributes=freeze_attributes(
                {
                    "instance": f"t.me/{channel.username}",
                    "account": f"@{channel.username}",
                    "display_name": title,
                    "operator": channel.operator,
                    "topic": channel.topic,
                    "viewpoint": channel.viewpoint,
                    "selection_reason": channel.reason,
                    "post_number": post.number,
                    "views": post.views,
                    "media": 0,
                    "excerpt_only": True,
                }
            ),
            content_hash=content_hash(post.key, post.text[:200]),
        )
