"""Credibility grading from corroboration and context, never from a source's own reliability.

Stories are clusters of events that report the same thing: near-identical or similar
titles within a window, or (for disasters) the same subtype close in space and time.
Within a story, sources with different parent organisations are independent, except
that syndicated copies (near-identical text) count once. See docs/03 section 4.3.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.domain.events import Category, Credibility, Event, Point

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "were",
        "will",
        "with",
        "over",
        "after",
        "into",
        "amid",
        "say",
        "says",
        "said",
        "new",
        "more",
        "than",
        "this",
        "their",
        "they",
        "what",
        "when",
        "who",
        "how",
        "why",
        "been",
        "being",
        "also",
        "about",
        "against",
        "between",
        "during",
        "before",
        "under",
        "his",
        "her",
        "not",
        "but",
        "out",
        "off",
        "all",
        "any",
        "can",
        "may",
        "now",
        "one",
        "two",
        "amid",
        "via",
        "per",
    ]
)
MIN_TOKEN_LENGTH = 3
STORY_SIMILARITY = 0.4
COPY_SIMILARITY = 0.85
MIN_SHARED_TOKENS = 3
TEXT_WINDOW = timedelta(hours=48)
GEO_WINDOW = timedelta(hours=12)
GEO_RADIUS_KM = 150.0
EARTH_RADIUS_KM = 6371.0
GEO_LINKED_CATEGORIES = frozenset({Category.DISASTER})

_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class SourceProfile:
    """What grading needs to know about a source, taken from the registry."""

    source_id: str
    independence_key: str
    name: str
    instrument: bool = False
    flags: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Graded:
    event: Event
    credibility: Credibility
    rationale: str
    story_id: str

    @property
    def changed(self) -> bool:
        event = self.event
        return (
            event.credibility is not self.credibility
            or event.story_id != self.story_id
            or event.grade_rationale != self.rationale
        )

    def apply(self) -> Event:
        return self.event.with_changes(
            credibility=self.credibility, grade_rationale=self.rationale, story_id=self.story_id
        )


def stem(token: str) -> str:
    """Crude English stemming so "enters", "entered" and "entering" meet as "enter"."""
    if token.endswith("ies") and len(token) >= 5:
        return token[:-3] + "y"
    if token.endswith("ing") and len(token) >= 6:
        return token[:-3]
    if token.endswith("ed") and len(token) >= 5:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) >= 4:
        return token[:-1]
    return token


def title_tokens(event: Event) -> frozenset[str]:
    text = (event.title_en or event.title).lower()
    tokens: set[str] = set()
    for raw in _TOKEN.findall(text):
        if len(raw) < MIN_TOKEN_LENGTH or raw in STOPWORDS:
            continue
        token = stem(raw)
        if len(token) >= MIN_TOKEN_LENGTH and token not in STOPWORDS:
            tokens.add(token)
    return frozenset(tokens)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def distance_km(a: Point, b: Point) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


class _UnionFind:
    def __init__(self, ids: Iterable[str]) -> None:
        self._parent = {item: item for item in ids}

    def find(self, item: str) -> str:
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[item] != root:
            self._parent[item], item = root, self._parent[item]
        return root

    def union(self, a: str, b: str) -> None:
        self._parent[self.find(a)] = self.find(b)


def _text_pairs(
    events: Sequence[Event], tokens: Mapping[str, frozenset[str]]
) -> set[tuple[str, str]]:
    index: dict[str, list[str]] = {}
    for event in events:
        for token in tokens[event.id]:
            index.setdefault(token, []).append(event.id)
    shared: dict[tuple[str, str], int] = {}
    for ids in index.values():
        for i, left in enumerate(ids):
            for right in ids[i + 1 :]:
                pair = (left, right) if left < right else (right, left)
                shared[pair] = shared.get(pair, 0) + 1
    by_id = {event.id: event for event in events}
    pairs: set[tuple[str, str]] = set()
    for (left, right), count in shared.items():
        if count < MIN_SHARED_TOKENS:
            continue
        gap = abs(by_id[left].published_at - by_id[right].published_at)
        if gap <= TEXT_WINDOW and jaccard(tokens[left], tokens[right]) >= STORY_SIMILARITY:
            pairs.add((left, right))
    return pairs


def _geo_pairs(events: Sequence[Event]) -> set[tuple[str, str]]:
    located = [e for e in events if e.point is not None and e.category in GEO_LINKED_CATEGORIES]
    pairs: set[tuple[str, str]] = set()
    for i, left in enumerate(located):
        for right in located[i + 1 :]:
            if left.subtype != right.subtype or left.point is None or right.point is None:
                continue
            if abs(left.published_at - right.published_at) > GEO_WINDOW:
                continue
            if distance_km(left.point, right.point) <= GEO_RADIUS_KM:
                pairs.add((left.id, right.id))
    return pairs


def build_stories(events: Sequence[Event]) -> list[list[Event]]:
    """Groups events into stories; each story is sorted oldest first."""
    tokens = {event.id: title_tokens(event) for event in events}
    groups = _UnionFind(event.id for event in events)
    for left, right in _text_pairs(events, tokens) | _geo_pairs(events):
        groups.union(left, right)
    members: dict[str, list[Event]] = {}
    for event in events:
        members.setdefault(groups.find(event.id), []).append(event)
    stories = [sorted(story, key=lambda e: (e.published_at, e.id)) for story in members.values()]
    stories.sort(key=lambda story: (story[0].published_at, story[0].id))
    return stories


def story_id_for(story: Sequence[Event]) -> str:
    return f"story-{story[0].id[:16]}"


def _independent_groups(
    story: Sequence[Event], profiles: Mapping[str, SourceProfile]
) -> tuple[dict[str, str], bool]:
    """Maps each event id to its independence group; near-identical copies join the first copy.

    The flag says whether any copy was folded across organisations (syndication).
    """
    tokens = {event.id: title_tokens(event) for event in story}
    group_of: dict[str, str] = {}
    syndicated = False
    for event in story:
        key = (
            profiles[event.source_id].independence_key
            if event.source_id in profiles
            else event.source_id
        )
        for other in story:
            if other.id == event.id or other.id not in group_of:
                continue
            if jaccard(tokens[event.id], tokens[other.id]) >= COPY_SIMILARITY:
                syndicated = syndicated or group_of[other.id] != key
                key = group_of[other.id]
                break
        group_of[event.id] = key
    return group_of, syndicated


def _source_name(event: Event, profiles: Mapping[str, SourceProfile]) -> str:
    profile = profiles.get(event.source_id)
    return profile.name if profile is not None else event.source_id


def _has_context(event: Event, pool: Sequence[Event]) -> int:
    count = 0
    for other in pool:
        if other.id == event.id or other.category is not event.category:
            continue
        if abs(other.published_at - event.published_at) > TEXT_WINDOW:
            continue
        same_country = event.country_iso is not None and other.country_iso == event.country_iso
        near = (
            event.point is not None
            and other.point is not None
            and distance_km(event.point, other.point) <= GEO_RADIUS_KM
        )
        if same_country or near:
            count += 1
    return count


def _grade_single(
    event: Event, profile: SourceProfile | None, pool: Sequence[Event]
) -> tuple[Credibility, str]:
    flags = profile.flags if profile is not None else frozenset()
    if profile is not None and (profile.instrument or "authoritative" in flags):
        return Credibility.PROBABLY_TRUE, "Instrument or authoritative data, no anomaly flags"
    if "state_controlled" in flags or "state_controlled" in event.tags:
        return (
            Credibility.POSSIBLY_TRUE,
            "State-controlled outlet, uncorroborated: treat as the government's position",
        )
    if "interested_party" in flags:
        return Credibility.POSSIBLY_TRUE, "Interested party, uncorroborated"
    context = _has_context(event, pool)
    if context > 0:
        where = event.country_iso or "the same area"
        kind = event.category.value
        return (
            Credibility.POSSIBLY_TRUE,
            f"Single source, consistent with {context} other {kind} item(s) in {where} this window",
        )
    return (
        Credibility.CANNOT_BE_JUDGED,
        "Single source, no corroboration and nothing else in the picture",
    )


def grade_events(events: Sequence[Event], profiles: Mapping[str, SourceProfile]) -> list[Graded]:
    """Grades every event in the pool; the pool should be one category within the window."""
    graded: list[Graded] = []
    for story in build_stories(events):
        story_id = story_id_for(story)
        groups, syndicated = _independent_groups(story, profiles)
        for event in story:
            others = {group for member_id, group in groups.items() if member_id != event.id}
            others.discard(groups[event.id])
            if len(others) >= 2:
                names = sorted({_source_name(m, profiles) for m in story if groups[m.id] in others})
                credibility = Credibility.CONFIRMED
                rationale = (
                    f"Confirmed by {len(others)} independent sources: {', '.join(names[:4])}"
                )
            elif len(others) == 1:
                other = next(m for m in story if groups[m.id] in others)
                credibility = Credibility.PROBABLY_TRUE
                rationale = (
                    f"Corroborated by {_source_name(other, profiles)} ({_gap(event, other)})"
                )
            else:
                credibility, rationale = _grade_single(event, profiles.get(event.source_id), events)
            if syndicated:
                rationale += "; syndicated copies counted once"
            graded.append(Graded(event, credibility, rationale, story_id))
    return graded


def _gap(event: Event, other: Event) -> str:
    delta: timedelta = other.published_at - event.published_at
    minutes = int(abs(delta).total_seconds() // 60)
    when = "later" if delta.total_seconds() >= 0 else "earlier"
    if minutes < 60:
        return f"{minutes} min {when}"
    hours = minutes // 60
    return f"{hours} h {when}"


def cutoff_for(now: datetime) -> datetime:
    return now - TEXT_WINDOW
