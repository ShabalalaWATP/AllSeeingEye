"""Mastodon hashtag timelines: public posts on instances the operator chose.

Posts are social listening at doctrine's floor (reliability E, credibility 6) until
corroborated. The instance decides what its public timeline shows; the connector never
authenticates. Content arrives as HTML and is reduced to text before it is stored.

One connector reads several hashtags from one instance, so a tag the instance has
retired must not cost the rest of that instance's tags: 404 and 410 skip that tag.
Everything else, including a rate limit, still fails the poll so the scheduler owns the
backoff and the upstream's `Retry-After`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.adapters.feeds.http_contracts import FeedHttpStatusError
from ase.adapters.feeds.mastodon_watch import DEFAULT_POLL_MINUTES, MAX_TAGS_PER_INSTANCE
from ase.application.feeds.pipeline import strip_html
from ase.application.ports import Clock
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

LIMIT = 40
MISSING_TAG_STATUSES = frozenset({404, 410})
TITLE_CHARS = 140
MAX_STATUSES = 400


def spec_for(instance: str, minutes: int = DEFAULT_POLL_MINUTES) -> SourceSpec:
    slug = instance.replace(".", "_").replace("-", "_")
    return SourceSpec(
        id=f"mastodon_{slug}",
        name=f"Mastodon hashtags ({instance})",
        organisation=instance,
        category=Category.SOCIAL,
        kind=SourceKind.API,
        url=f"https://{instance}/api/v1/timelines/tag/",
        reliability=Reliability.E,
        poll_interval=timedelta(minutes=minutes),
        licence_note="Instance rules; public posts, text and links only",
        homepage=f"https://{instance}/",
        language="und",
    )


def _when(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


def _title(text: str) -> str:
    first = text.split(". ", maxsplit=1)[0].strip()
    candidate = first if 20 <= len(first) <= TITLE_CHARS else text
    return candidate if len(candidate) <= TITLE_CHARS else candidate[: TITLE_CHARS - 1] + "…"


class MastodonConnector:
    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        instance: str,
        tags: Sequence[str],
        minutes: int = DEFAULT_POLL_MINUTES,
    ) -> None:
        self.spec = spec_for(instance, minutes)
        self._http = http
        self._clock = clock
        cleaned = tuple(tag.strip().lstrip("#").lower() for tag in tags if tag.strip())
        self._tags = cleaned[:MAX_TAGS_PER_INSTANCE]

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        seen: dict[str, Event] = {}
        for tag in self._tags:
            try:
                data = await self._http.get_json(f"{self.spec.url}{tag}?limit={LIMIT}")
            except NotModified:
                continue
            except FeedHttpStatusError as exc:
                # A retired or hidden tag on this instance; its siblings still poll.
                # Anything else (auth, rate limit, instance fault) fails the whole poll
                # so health, the breaker and the scheduler's backoff all see it.
                if exc.status_code not in MISSING_TAG_STATUSES:
                    raise
                continue
            statuses = [s for s in data if isinstance(s, dict)] if isinstance(data, list) else []
            for status in statuses[:MAX_STATUSES]:
                event = self._to_event(status, now)
                if event is not None:
                    seen.setdefault(event.id, event)
        return list(seen.values())

    def _to_event(self, status: dict[str, Any], now: datetime) -> Event | None:
        status_id = str(status.get("id") or "").strip()
        text = strip_html(str(status.get("content") or "")) or ""
        url = str(status.get("url") or status.get("uri") or "")
        if not status_id or not text or not url.startswith("https://"):
            return None
        raw_account = status.get("account")
        account: dict[str, Any] = raw_account if isinstance(raw_account, dict) else {}
        acct = str(account.get("acct") or "unknown")
        hashtags = [
            str(tag.get("name") or "").lower()
            for tag in status.get("tags", [])
            if isinstance(tag, dict) and tag.get("name")
        ]
        language = status.get("language")
        media = status.get("media_attachments")
        return Event(
            id=event_id(self.spec.id, status_id),
            source_id=self.spec.id,
            category=Category.SOCIAL,
            subtype="post",
            title=_title(text),
            summary=text[:2_000],
            url=url,
            published_at=_when(status.get("created_at"), now),
            observed_at=now,
            geo_confidence=GeoConfidence.NONE,
            country_iso=None,
            language=str(language) if isinstance(language, str) and language else "und",
            tags=frozenset({"mastodon", *hashtags[:12]}),
            severity=None,
            reliability=self.spec.reliability,
            credibility=Credibility.CANNOT_BE_JUDGED,
            grade_rationale="Public social post; not corroborated",
            attributes=freeze_attributes(
                {
                    "instance": self.spec.organisation,
                    "account": acct,
                    "display_name": str(account.get("display_name") or "") or None,
                    "boosts": status.get("reblogs_count"),
                    "favourites": status.get("favourites_count"),
                    "replies": status.get("replies_count"),
                    "media": len(media) if isinstance(media, list) else 0,
                    "sensitive": bool(status.get("sensitive")),
                }
            ),
            content_hash=content_hash(status_id, text[:200]),
        )
