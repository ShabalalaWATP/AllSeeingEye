"""Warning rules consider all retained matches, independently of display page sizes."""

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from typing import Literal, cast

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.warning.evaluator import evaluate_candidates
from ase.domain.events import BoundingBox, Category, Event, Point
from ase.domain.warning import Indicator
from feeds_helpers import make_event
from test_exact_reusable_areas import triangle
from test_warning import NOW, indicator

SCOPES = ("global", "country", "bbox", "exact-area")


def scoped_rule(scope: str, *, threshold: int = 1) -> Indicator:
    rule = indicator(countries=(), severity_floor=0.7, threshold=threshold)
    if scope == "country":
        return replace(rule, countries=("UA",))
    if scope == "bbox":
        return replace(rule, bbox=BoundingBox(10, 40, 12, 42))
    if scope == "exact-area":
        return replace(rule, research_area=triangle())
    return rule


def matching_event(key: str, *, age_seconds: int = 0) -> Event:
    return make_event(
        key,
        category=Category.CONFLICT,
        title="Shelling in Kharkiv",
        country_iso="UA",
        point=Point(10.2, 40.2),
        severity=0.8,
        published_at=NOW - timedelta(seconds=age_seconds),
    )


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("nonmatching_field", ["keyword", "severity"])
async def test_older_match_survives_more_than_2000_newer_nonmatches(
    scope: str, nonmatching_field: str
) -> None:
    store = InMemoryEventStore()
    older_match = matching_event("older-match", age_seconds=5 * 3600)
    newer = [matching_event(f"newer-{index}") for index in range(2_001)]
    if nonmatching_field == "keyword":
        newer = [replace(event, title="Talks in Kyiv") for event in newer]
    else:
        newer = [replace(event, severity=0.1) for event in newer]
    store.upsert([older_match, *newer])

    firing = await evaluate_candidates(store, scoped_rule(scope), NOW, None)

    assert firing is not None
    assert firing.count == 1
    assert firing.evidence == (older_match,)
    assert firing.countries == ("UA",)


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("threshold", [2_001, 10_000])
async def test_high_threshold_counts_all_matches_and_keeps_twenty_newest_evidence(
    scope: str, threshold: int
) -> None:
    store = InMemoryEventStore()
    events = [
        matching_event(f"match-{index}", age_seconds=index) for index in range(threshold + 37)
    ]
    store.upsert(events)

    firing = await evaluate_candidates(store, scoped_rule(scope, threshold=threshold), NOW, None)

    assert firing is not None
    assert firing.count == len(events)
    assert firing.evidence == tuple(events[:20])
    assert firing.countries == ("UA",)


async def test_country_union_counts_each_event_once_and_retains_countries_beyond_evidence() -> None:
    store = InMemoryEventStore()
    newest = [matching_event(f"ukraine-{index}", age_seconds=index) for index in range(25)]
    older = replace(matching_event("poland", age_seconds=60), country_iso="PL")
    outside = replace(matching_event("outside"), country_iso="SD")
    store.upsert([*newest, older, outside])
    rule = replace(scoped_rule("country"), countries=("UA", "PL", "UA", "PL"))

    firing = await evaluate_candidates(store, rule, NOW, None)

    assert firing is not None
    assert firing.count == 26
    assert firing.evidence == tuple(newest[:20])
    assert firing.countries == ("UA", "PL")


@pytest.mark.parametrize("scope", SCOPES)
async def test_timestamp_ties_have_deterministic_evidence_order(scope: str) -> None:
    store = InMemoryEventStore()
    events = [replace(matching_event(str(index)), id=f"tie-{index:02d}") for index in range(30)]
    store.upsert(events[::2] + events[1::2])

    firing = await evaluate_candidates(store, scoped_rule(scope), NOW, None)

    assert firing is not None
    assert firing.count == 30
    assert [event.id for event in firing.evidence] == [
        f"tie-{index:02d}" for index in range(29, 9, -1)
    ]


@pytest.mark.parametrize("scope", SCOPES)
async def test_synchronous_store_fallback_retains_complete_matches(scope: str) -> None:
    store = InMemoryEventStore()
    events = [matching_event(f"match-{index}", age_seconds=index) for index in range(2_017)]
    store.upsert(events)
    query_only_store = cast(EventStore, SimpleNamespace(query=store.query))

    firing = await evaluate_candidates(
        query_only_store, scoped_rule(scope, threshold=2_001), NOW, None
    )

    assert firing is not None
    assert firing.count == len(events)
    assert firing.evidence == tuple(events[:20])


def test_complete_query_preserves_all_filters() -> None:
    store = InMemoryEventStore()
    expected = matching_event("inside", age_seconds=30)
    excluded = [
        replace(expected, id="category", category=Category.NEWS),
        replace(expected, id="country", country_iso="PL"),
        replace(expected, id="source", source_id="other-source"),
        replace(expected, id="too-old", published_at=NOW - timedelta(seconds=61)),
        replace(expected, id="at-until", published_at=NOW),
        replace(expected, id="unknown-date", published_at=None),
        replace(expected, id="outside-bbox", point=Point(20, 50)),
        replace(expected, id="no-point", point=None),
    ]
    store.upsert([expected, *excluded])
    query = EventQuery(
        categories=frozenset({Category.CONFLICT}),
        country_iso="UA",
        source_ids=frozenset({"test_source"}),
        since=NOW - timedelta(seconds=60),
        until=NOW,
        bbox=BoundingBox(10, 40, 12, 42),
        limit=None,
    )

    assert store.query(query) == [expected]


@pytest.mark.parametrize(("offset", "sampling"), [(1, "newest"), (-1, "newest"), (0, "geographic")])
def test_complete_queries_refuse_pagination_or_sampling(
    offset: int, sampling: Literal["newest", "geographic"]
) -> None:
    with pytest.raises(ValueError, match="Complete selections cannot use pagination or sampling"):
        EventQuery(limit=None, offset=offset, sampling=sampling)
