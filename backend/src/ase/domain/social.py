"""Bounded social listening aggregates. Raw posts remain in the live store."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from ase.domain.collection import CollectionPlan
from ase.domain.events import Event

MAX_TERMS = 32
MAX_TERM_CHARS = 60
MIN_BASELINE_HOURS = 6
MIN_BURST_POSTS = 3
BURST_RATIO = 2.0
HASHTAG = re.compile(r"(?<!\w)#(\w{1,60})(?!\w)", re.UNICODE)
PLATFORMS = ("mastodon", "reddit", "telegram", "youtube")


@dataclass(frozen=True, slots=True)
class WatchedTerm:
    term: str
    public: bool
    owners: frozenset[UUID] = frozenset()
    team_ids: frozenset[UUID] = frozenset()

    @property
    def key(self) -> str:
        return hashlib.sha256(self.term.encode()).hexdigest()[:32]


@dataclass(frozen=True, slots=True)
class SocialBaseline:
    mean: float
    hours: int


@dataclass(frozen=True, slots=True)
class KeywordActivity:
    term: str
    count: int
    baseline: float | None
    baseline_hours: int

    @property
    def ratio(self) -> float | None:
        if self.baseline is None or self.baseline == 0:
            return None
        return round(self.count / self.baseline, 2)

    @property
    def burst(self) -> bool:
        return (
            self.baseline is not None
            and self.baseline_hours >= MIN_BASELINE_HOURS
            and self.count >= MIN_BURST_POSTS
            and self.count >= self.baseline * BURST_RATIO
        )


@dataclass(frozen=True, slots=True)
class PlatformActivity:
    platform: str
    instance: str
    count: int
    located: int


@dataclass(frozen=True, slots=True)
class HashtagActivity:
    tag: str
    count: int


def normalise_term(value: str) -> str:
    return " ".join(value.strip().casefold().lstrip("#").split())[:MAX_TERM_CHARS]


def vocabulary(watch: Iterable[str], plans: Sequence[CollectionPlan]) -> tuple[WatchedTerm, ...]:
    """A stable global cap, prioritising the operator's packaged watchlist.

    Keep ownership beside each term so private collection vocabulary is never exposed
    on another user's board. Only the digest of a selected term reaches activity_samples.
    """
    public = {normalise_term(term) for term in watch if normalise_term(term)}
    owners: dict[str, set[UUID]] = {}
    teams: dict[str, set[UUID]] = {}
    for plan in plans:
        if plan.enabled:
            for value in plan.search_terms():
                term = normalise_term(value)
                if term:
                    if plan.team_id is None:
                        owners.setdefault(term, set()).add(plan.created_by)
                    else:
                        teams.setdefault(term, set()).add(plan.team_id)
    selected = (sorted(public) + sorted((set(owners) | set(teams)) - public))[:MAX_TERMS]
    return tuple(
        WatchedTerm(
            term, term in public, frozenset(owners.get(term, ())), frozenset(teams.get(term, ()))
        )
        for term in selected
    )


def keyword_counts(events: Sequence[Event], terms: Sequence[WatchedTerm]) -> Mapping[str, int]:
    """Count matching posts, not repeated mentions. Escape configuration before compiling."""
    patterns = {
        term.key: re.compile(r"(?<!\w)" + re.escape(term.term) + r"(?!\w)") for term in terms
    }
    counts = dict.fromkeys(patterns, 0)
    for event in events:
        text = f"{event.title} {event.summary or ''} {' '.join(event.tags)}".casefold()
        for key, pattern in patterns.items():
            if pattern.search(text):
                counts[key] += 1
    return counts


def platform_groups(events: Sequence[Event]) -> tuple[PlatformActivity, ...]:
    counts: Counter[tuple[str, str]] = Counter()
    located: Counter[tuple[str, str]] = Counter()
    for event in events:
        platform = next((name for name in PLATFORMS if name in event.tags), "other")
        instance = event.attributes.get("instance")
        if not isinstance(instance, str) or not instance:
            instance = event.source_id if platform in {"mastodon", "other"} else platform
        key = (platform, instance[:120])
        counts[key] += 1
        located[key] += event.point is not None
    return tuple(
        PlatformActivity(platform, instance, count, located[(platform, instance)])
        for (platform, instance), count in sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    )


def top_hashtags(events: Sequence[Event], limit: int = 20) -> tuple[HashtagActivity, ...]:
    counts: Counter[str] = Counter()
    for event in events:
        tags = set(HASHTAG.findall(f"{event.title} {event.summary or ''}".casefold()))
        if "mastodon" in event.tags:
            tags.update(
                tag.casefold()
                for tag in event.tags
                if tag not in PLATFORMS and re.fullmatch(r"\w{1,60}", tag)
            )
        counts.update(tags)
    return tuple(
        HashtagActivity(tag, count)
        for tag, count in sorted(counts.items(), key=lambda row: (-row[1], row[0]))[:limit]
    )
