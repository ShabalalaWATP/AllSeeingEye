"""Minimal private feed projection, deliberately excluding report content."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FeedToken:
    user_id: UUID
    token_hash: str
    security_version: int
    created_at: datetime
    include_titles: bool = False


@dataclass(frozen=True, slots=True)
class FeedEntry:
    id: UUID
    kind: str
    title: str
    path: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PrivateFeed:
    user_id: UUID
    entries: tuple[FeedEntry, ...]
    generated_at: datetime
    truncated: bool


@dataclass(frozen=True, slots=True)
class FeedStatus:
    enabled: bool
    include_titles: bool
    created_at: datetime | None


@dataclass(frozen=True, slots=True)
class IssuedFeedToken:
    token: str
    feed_url: str
    username: str = "feed"
