"""Bounded public-record snapshots and safe, single-request collection receipts."""

import asyncio
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    JsonScalar,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch

MAX_RESULTS = 20


def text(value: Any, limit: int = 300) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def domain_name(value: Any) -> str | None:
    """Require an explicit public-style DNS name; never derive identity from a URL or IP."""
    if not isinstance(value, str) or not value or any(char in value for char in "/:@?#\\"):
        return None
    try:
        name = value.strip().removesuffix(".").encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None
    labels = name.split(".")
    if len(name) > 253 or len(labels) < 2 or not re.fullmatch(r"[a-z][a-z0-9-]*", labels[-1]):
        return None
    if labels[-1] in {"localhost", "local", "internal", "test", "invalid", "example", "onion"}:
        return None
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part) for part in labels):
        return None
    return name


def receipt(
    source_id: str,
    name: str,
    status: CollectionStatus,
    explanation: str,
    items: Sequence[Event] = (),
) -> ResearchBatch:
    return ResearchBatch(
        tuple(items),
        (CollectionAttempt(source_id, name, status, len(items), explanation, "en"),),
    )


async def collect_json(
    http: FeedHttpClient,
    source_id: str,
    name: str,
    url: str,
    parse: Callable[[dict[str, Any]], Sequence[Event]],
    explanation: str,
) -> ResearchBatch:
    try:
        async with asyncio.timeout(20):
            payload = await http.get_json(url, conditional=False, max_redirects=0)
        if not isinstance(payload, dict):
            raise ValueError("Expected public record object")
        items = tuple(parse(payload))[:MAX_RESULTS]
    except TimeoutError:
        return receipt(
            source_id, name, CollectionStatus.TIMED_OUT, "Public-record request timed out."
        )
    except (FeedFetchError, NotModified, ValueError, TypeError, KeyError, OverflowError):
        return receipt(
            source_id,
            name,
            CollectionStatus.FAILED,
            "Public-record service was unavailable or returned an unusable response. "
            "No retry was made.",
        )
    return receipt(
        source_id,
        name,
        CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
        explanation,
        items,
    )


def record_event(
    source_id: str,
    key: str,
    title: str,
    summary: str,
    url: str,
    observed: datetime,
    *,
    category: Category,
    attributes: Mapping[str, JsonScalar],
    published: datetime | None = None,
) -> Event:
    title, summary = text(title), text(summary, 2000)
    return Event(
        id=event_id(source_id, key),
        source_id=source_id,
        category=category,
        subtype="public_record",
        title=title,
        published_at=published or observed,
        observed_at=observed,
        reliability=Reliability.B,
        summary=summary,
        url=url,
        credibility=Credibility.CANNOT_BE_JUDGED,
        grade_rationale=(
            "Public service record or filing metadata; underlying claims are not "
            "independently verified."
        ),
        tags=frozenset({"research_record"}),
        attributes=freeze_attributes(attributes),
        content_hash=content_hash(title, summary),
    )
