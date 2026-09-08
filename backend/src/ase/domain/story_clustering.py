"""Bounded-window text/place clustering for navigation, never corroboration."""

from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime
from itertools import chain

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
from ase.domain.evidence_time import publication_order
from ase.domain.similarity_candidates import MAX_CANDIDATES, token_candidate_pairs
from ase.domain.source_provenance import DisjointGroups


def _text_pairs(
    events: Sequence[Event], tokens: Mapping[str, frozenset[str]]
) -> Iterator[tuple[str, str]]:
    # Date order preserves transitive time-window links between exact duplicates.
    ordered = sorted(events, key=lambda event: (publication_order(event), event.id))
    words = [tokens[event.id] for event in ordered]
    for left, right in token_candidate_pairs(words):
        if len(words[left] & words[right]) < MIN_SHARED_TOKENS:
            continue
        first, second = ordered[left], ordered[right]
        if first.published_at is None or second.published_at is None:
            continue
        if (
            abs(first.published_at - second.published_at) <= TEXT_WINDOW
            and jaccard(words[left], words[right]) >= STORY_SIMILARITY
        ):
            yield first.id, second.id


def _geo_pairs(events: Sequence[Event]) -> Iterator[tuple[str, str]]:
    located = [e for e in events if e.point is not None and e.category in GEO_LINKED_CATEGORIES]
    located.sort(key=lambda event: (publication_order(event), event.id))
    for i, left in enumerate(located):
        for right in located[i + 1 : i + 1 + MAX_CANDIDATES]:
            if left.subtype != right.subtype or left.point is None or right.point is None:
                continue
            if left.published_at is None or right.published_at is None:
                continue
            if abs(left.published_at - right.published_at) > GEO_WINDOW:
                continue
            if distance_km(left.point, right.point) <= GEO_RADIUS_KM:
                yield left.id, right.id


def build_stories(events: Sequence[Event]) -> list[list[Event]]:
    """Groups related topics for navigation, without asserting they report the same claim."""
    tokens = {event.id: title_tokens(event) for event in events}
    groups = DisjointGroups(event.id for event in events)
    for left, right in chain(_text_pairs(events, tokens), _geo_pairs(events)):
        groups.union(left, right)
    members: dict[str, list[Event]] = {}
    for event in events:
        members.setdefault(groups.find(event.id), []).append(event)

    def order(event: Event) -> tuple[bool, datetime, str]:
        return event.published_at is None, publication_order(event), event.id

    stories = [sorted(story, key=order) for story in members.values()]
    stories.sort(key=lambda story: order(story[0]))
    return stories


def story_id_for(story: Sequence[Event]) -> str:
    return f"story-{story[0].id[:16]}"
