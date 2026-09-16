"""Strict mapping from one public Bluesky feed item to a graded social event.

Nothing is followed: embedded links, quoted posts, media blobs and thread parents are
described by count only. Reposts are skipped because the reposting account did not write
the words; replies are kept only when the author's own thread carries readable text.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

from ase.adapters.feeds.bluesky_accounts import BlueskyAccount
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceSpec

POST_TYPE: Final = "app.bsky.feed.post"
COLLECTION: Final = f"/{POST_TYPE}/"
TITLE_CHARS: Final = 140
EXCERPT_CHARS: Final = 600
MIN_REPLY_CHARS: Final = 120
MAX_RKEY = 40
MAX_LANGUAGE = 16
RATIONALE: Final = (
    "Public Bluesky post read from the author's own feed; the account, its claims and any "
    "linked material are unassessed and uncorroborated."
)


def record_key(uri: str) -> str | None:
    """The post's record key from its AT-URI, or None when the shape is not a post."""
    if not uri.startswith("at://") or COLLECTION not in uri:
        return None
    rkey = uri.rsplit(COLLECTION, maxsplit=1)[1]
    if not rkey or len(rkey) > MAX_RKEY or not all(char.isalnum() for char in rkey):
        return None
    return rkey


def post_url(handle: str, rkey: str) -> str:
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def created_at(value: object, now: datetime) -> datetime:
    """Author-supplied times are not trusted ahead of the clock; future stamps clamp to now."""
    if not isinstance(value, str) or len(value) > 40:
        return now
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return now
    moment = (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)
    return now if moment > now else moment


def _language(record: dict[str, Any]) -> str:
    langs = record.get("langs")
    first = langs[0] if isinstance(langs, list) and langs else None
    if not isinstance(first, str) or not 2 <= len(first) <= MAX_LANGUAGE:
        return "und"
    if not all(char.isascii() and (char.isalnum() or char == "-") for char in first):
        return "und"
    return first.lower()


def _title(text: str) -> str:
    first = text.split(". ", maxsplit=1)[0].strip()
    candidate = first if 20 <= len(first) <= TITLE_CHARS else text
    return candidate if len(candidate) <= TITLE_CHARS else candidate[: TITLE_CHARS - 1] + "…"


def _media_count(post: dict[str, Any]) -> int:
    embed = post.get("embed")
    if not isinstance(embed, dict):
        return 0
    images = embed.get("images")
    if isinstance(images, list):
        return len(images)
    return 1 if embed.get("$type") or embed.get("external") or embed.get("record") else 0


def _handle(author: dict[str, Any]) -> str:
    return str(author.get("handle", "")).strip().lower()


def _counter(post: dict[str, Any], key: str) -> int | None:
    value = post.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _accepted(
    item: Any, account: BlueskyAccount
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str, bool] | None:
    """Every admission rule in one place: post, record, author, key, text and reply flag."""
    if not isinstance(item, dict) or "reason" in item:
        return None  # a repost: the words belong to another account
    post = item.get("post")
    if not isinstance(post, dict):
        return None
    record, author = post.get("record"), post.get("author")
    if not isinstance(record, dict) or not isinstance(author, dict):
        return None
    # Only a post record, and only from the account whose feed was requested.
    if record.get("$type") != POST_TYPE or _handle(author) != account.handle:
        return None
    rkey = record_key(str(post.get("uri", "")))
    text = " ".join(str(record.get("text") or "").split())
    is_reply = isinstance(record.get("reply"), dict)
    # A short reply inside the author's own thread is not worth reading on its own.
    if rkey is None or not text or (is_reply and len(text) < MIN_REPLY_CHARS):
        return None
    return post, record, author, rkey, text, is_reply


def to_event(item: Any, account: BlueskyAccount, spec: SourceSpec, now: datetime) -> Event | None:
    """Map one `feed` entry, or return None when it must not become an event."""
    accepted = _accepted(item, account)
    if accepted is None:
        return None
    post, record, author, rkey, text, is_reply = accepted
    return Event(
        id=event_id(spec.id, rkey),
        source_id=spec.id,
        category=Category.SOCIAL,
        subtype="post",
        title=_title(text),
        summary=text[:EXCERPT_CHARS],
        url=post_url(account.handle, rkey),
        published_at=created_at(record.get("createdAt"), now),
        observed_at=now,
        geo_confidence=GeoConfidence.NONE,
        country_iso=None,
        language=_language(record),
        tags=account.tags,
        severity=None,
        reliability=spec.reliability,
        credibility=Credibility.CANNOT_BE_JUDGED,
        grade_rationale=RATIONALE,
        attributes=freeze_attributes(
            {
                "account": account.handle,
                # The social board groups a platform by "instance"; here that is
                # the account itself, because each account is its own source.
                "instance": account.handle,
                "display_name": str(author.get("displayName") or "") or None,
                "operator": account.operator,
                "topic": account.topic,
                "viewpoint": account.viewpoint,
                "registry_reason": account.reason,
                "thread_reply": is_reply,
                "excerpt_truncated": len(text) > EXCERPT_CHARS,
                "media_attachments": _media_count(post),
                "likes": _counter(post, "likeCount"),
                "reposts": _counter(post, "repostCount"),
                "replies": _counter(post, "replyCount"),
                "quotes": _counter(post, "quoteCount"),
                "profile_url": account.profile_url,
            }
        ),
        content_hash=content_hash(rkey, text[:200]),
    )
