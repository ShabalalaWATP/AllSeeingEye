"""Bounded-window text/place clustering for navigation, never corroboration."""

from collections.abc import Mapping, Sequence

from ase.domain.event_similarity import (
    GEO_LINKED_CATEGORIES,
    GEO_RADIUS_KM,
    GEO_WINDOW,
    MIN_SHARED_TOKENS,
    STORY_SIMILARITY,
    TEXT_WINDOW,
    distance_km,
    jaccard,
    title_tokens,
)
from ase.domain.events import Event
from ase.domain.source_provenance import DisjointGroups


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
    """Groups related topics for navigation, without asserting they report the same claim."""
    tokens = {event.id: title_tokens(event) for event in events}
    groups = DisjointGroups(event.id for event in events)
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
