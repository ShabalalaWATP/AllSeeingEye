"""A trailing warning window includes both boundaries and rejects future publications."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.warning import evaluator
from ase.application.warning.evaluator import evaluate_candidates
from ase.domain.warning import evaluate
from test_warning import NOW
from test_warning_volume import SCOPES, matching_event, scoped_rule


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize(
    ("publication", "expected"),
    [
        (NOW, True),
        (NOW - timedelta(hours=6), True),
        (NOW - timedelta(hours=6, microseconds=1), False),
        (NOW + timedelta(microseconds=1), False),
        (NOW + timedelta(days=7), False),
        (None, False),
        (NOW.replace(tzinfo=None), False),
    ],
)
async def test_domain_and_store_agree_on_closed_publication_window(scope, publication, expected):
    event = replace(matching_event("boundary"), published_at=publication)
    rule = scoped_rule(scope)
    store = InMemoryEventStore()
    store.upsert([event])
    domain = evaluate(rule, [event], NOW, None)
    selected = await evaluate_candidates(store, rule, NOW, None)
    assert (domain is not None) is expected
    assert selected == domain


async def test_store_excludes_future_events_before_domain_projection(monkeypatch):
    store = InMemoryEventStore()
    current = matching_event("current")
    future = replace(current, id="future", published_at=NOW + timedelta(microseconds=1))
    store.upsert([current, future])
    projection = Mock(wraps=evaluate)
    monkeypatch.setattr(evaluator, "evaluate", projection)

    await evaluate_candidates(store, scoped_rule("exact-area"), NOW, None)

    assert projection.call_args.args[1] == [current]


async def test_future_schedule_metadata_does_not_make_current_publication_future():
    event = replace(matching_event("scheduled"), attributes={"net": "2027-01-01T00:00:00Z"})
    store = InMemoryEventStore()
    store.upsert([event])
    firing = await evaluate_candidates(store, scoped_rule("global"), NOW, None)
    assert firing is not None and firing.evidence == (event,)


async def test_latest_representable_clock_still_includes_exact_boundary():
    now = datetime.max.replace(tzinfo=UTC)
    event = replace(matching_event("latest"), published_at=now)
    store = InMemoryEventStore()
    store.upsert([event])
    firing = await evaluate_candidates(store, scoped_rule("global"), now, None)
    assert firing is not None and firing.evidence == (event,)
