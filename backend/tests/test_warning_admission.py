"""Every warning scope evaluates an admitted immutable snapshot off the event loop."""

import asyncio
import threading
from dataclasses import replace
from datetime import datetime

import pytest

from ase.adapters.store import memory
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.application.warning import evaluator
from ase.domain.events import Event
from ase.domain.warning import Firing, Indicator
from test_warning import NOW
from test_warning_volume import SCOPES, matching_event, scoped_rule


@pytest.mark.parametrize("scope", SCOPES)
async def test_all_scopes_filter_and_evaluate_one_snapshot_off_loop(
    scope: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = InMemoryEventStore()
    original_event = matching_event("original")
    store.upsert([original_event])
    entered, release = threading.Event(), threading.Event()
    loop_thread = threading.get_ident()
    original_select, original_evaluate = memory.select_events, evaluator.evaluate

    def select(snapshot: list[Event], query: EventQuery) -> list[Event]:
        assert threading.get_ident() != loop_thread, "filtering must run off the event loop"
        entered.set()
        assert release.wait(5), "the event loop must remain responsive during filtering"
        return original_select(snapshot, query)

    def evaluate(
        rule: Indicator, events: list[Event], now: datetime, last: datetime | None
    ) -> Firing | None:
        assert threading.get_ident() != loop_thread, "matching must run off the event loop"
        return original_evaluate(rule, events, now, last)

    monkeypatch.setattr(memory, "select_events", select)
    monkeypatch.setattr(evaluator, "evaluate", evaluate)
    pending = asyncio.create_task(
        evaluator.evaluate_candidates(store, scoped_rule(scope), NOW, None)
    )
    try:
        async with asyncio.timeout(5):
            while not entered.is_set():
                await asyncio.sleep(0)
        changed = replace(original_event, title="Talks in Kyiv")
        store.put([changed, matching_event("arrived-after-snapshot")])
    finally:
        release.set()

    firing = await pending
    assert firing is not None
    assert firing.count == 1
    assert firing.evidence == (original_event,)
    assert store.get(original_event.id) == changed


@pytest.mark.parametrize("scope", SCOPES)
async def test_waiting_warning_captures_matches_only_after_admission(scope: str) -> None:
    store = InMemoryEventStore()
    first_match = matching_event("first", age_seconds=60)
    later_match = matching_event("arrived-while-waiting")
    store.upsert([first_match])
    entered, release = threading.Event(), threading.Event()

    def blocked_projection(events: list[Event]) -> list[Event]:
        entered.set()
        assert release.wait(5), "the waiting warning must not block the event loop"
        return events

    occupying = asyncio.create_task(
        store.read_cooperatively(EventQuery(), blocked_projection, admission_key="test:other-read")
    )
    pending = None
    try:
        async with asyncio.timeout(5):
            while not entered.is_set():
                await asyncio.sleep(0)
        pending = asyncio.create_task(
            evaluator.evaluate_candidates(store, scoped_rule(scope, threshold=2), NOW, None)
        )
        await asyncio.sleep(0)
        assert not pending.done()
        store.upsert([later_match])
    finally:
        release.set()
        await occupying

    assert pending is not None
    firing = await pending
    assert firing is not None
    assert firing.count == 2
    assert firing.evidence == (later_match, first_match)
