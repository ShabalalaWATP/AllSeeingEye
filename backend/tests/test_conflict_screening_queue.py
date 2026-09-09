"""Shared screening is bounded and never resurrects stale or disabled evidence."""

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.conflict_screening.inputs import candidates, source_text
from ase.application.conflict_screening.queue import ConflictScreeningQueue, ScreeningGeneration
from ase.application.conflict_screening.records import ScreeningVerdict
from ase.domain.events import Category, Credibility
from feeds_helpers import NOW, make_event
from helpers import FakeClock
from test_model_routing import profile


def pair(key="a", title="Military forces exchange artillery fire"):
    source = make_event(key, source_id="rss", category=Category.NEWS, title=title).with_changes(
        attributes={"outlet": "Public outlet"}
    )
    target = make_event(key, source_id="gdelt_events", category=Category.CONFLICT).with_changes(
        attributes={"event_code": "173", "actor1": "original actor"}
    )
    return source, target


class Runtime:
    def __init__(self):
        self.generation = ScreeningGeneration("one", profile())

    async def resolve(self):
        return self.generation

    @asynccontextmanager
    async def release(self, generation):
        yield self.generation is not None and generation.key == self.generation.key


@pytest.fixture
def rig():
    store, bus, model, admission = InMemoryEventStore(), AsyncMock(), AsyncMock(), AsyncMock()
    allowed = {"rss": True, "gdelt_events": True}
    admission.enabled_many.side_effect = lambda ids: {key: allowed.get(key, False) for key in ids}
    runtime, clock = Runtime(), FakeClock(NOW)
    model.screen.side_effect = lambda p, items: {
        item.key: ScreeningVerdict("armed_conflict", "Reports organised fighting.", item.title)
        for item in items
    }
    queue = ConflictScreeningQueue(store, bus, model, runtime, admission, clock, calls_per_hour=1)
    return SimpleNamespace(**locals())


async def test_exact_feed_text_is_required_and_cached_for_later_machine_reports(rig):
    source, target = pair()
    rig.store.upsert([target])
    assert await rig.queue.run_once() == 0
    rig.model.screen.assert_not_called()
    rig.store.upsert([source])
    assert await rig.queue.run_once() == 2
    sent = rig.model.screen.await_args.args[1]
    assert sent == [source_text(source)]
    assert rig.store.get(target.id).attributes["event_code"] == "173"
    assert rig.store.get(target.id).attributes["conflict_screening_source"] == "rss"
    assert await rig.queue.run_once() == 0
    rig.store.upsert([target.with_changes(id="another-machine-record")])
    assert await rig.queue.run_once() == 1
    assert rig.model.screen.await_count == 1


def test_never_uses_generated_labels_url_slugs_unjoined_or_non_feed_text():
    source, target = pair()
    assert not candidates([target])
    assert not candidates([source.with_changes(attributes={}), target])
    assert not candidates([source.with_changes(category=Category.CONFLICT), target])
    other = source.with_changes(url="https://another.example/a", title="Routine company filing")
    assert not candidates([other, target])
    copied = source.with_changes(url=source.url + "?utm_source=example")
    assert len(candidates([copied, target])) == 2


@pytest.mark.parametrize("blocked", ["no_model", "disabled", "source", "target"])
async def test_no_call_without_configuration_or_source_admission(rig, blocked):
    rig.store.upsert(pair())
    if blocked == "no_model":
        rig.runtime.generation = None
    elif blocked == "disabled":
        rig.queue._enabled = False
    else:
        rig.allowed["rss" if blocked == "source" else "gdelt_events"] = False
        if blocked == "target":
            # Source text alone is unrelated, so it is not an independent screening candidate.
            rig.store.put(pair(title="Routine company filing"))
    assert await rig.queue.run_once() == 0
    rig.model.screen.assert_not_called()


@pytest.mark.parametrize(
    "change", ["model", "source", "target", "prune", "revised", "enrich", "url", "hash"]
)
async def test_slow_result_rechecks_generation_sources_and_live_content(rig, change):
    source, target = pair()
    rig.store.upsert([source, target])
    entered, finish = asyncio.Event(), asyncio.Event()

    async def screen(p, items):
        entered.set()
        await finish.wait()
        return {
            item.key: ScreeningVerdict("unrelated", "Industrial accident.", "") for item in items
        }

    rig.model.screen.side_effect = screen
    task = asyncio.create_task(rig.queue.run_once())
    await entered.wait()
    assert await rig.queue.run_once() == 0  # No overlapping model calls.
    if change == "model":
        rig.runtime.generation = ScreeningGeneration("two", profile("different"))
    elif change in {"source", "target"}:
        rig.allowed["rss" if change == "source" else "gdelt_events"] = False
    elif change == "prune":
        rig.store.prune(NOW + timedelta(days=60))
    elif change == "revised":
        rig.store.put([source.with_changes(title="Revised source text")])
    elif change == "url":
        rig.store.put([source.with_changes(url="https://another.example/changed")])
    elif change == "hash":
        rig.store.put([source.with_changes(content_hash="changed")])
    else:
        rig.store.put(
            [target.with_changes(title_en="Translation", credibility=Credibility.CONFIRMED)]
        )
    finish.set()
    await task
    current = rig.store.get(target.id)
    if change == "prune":
        assert current is None
    elif change == "enrich":
        assert current.title_en == "Translation" and current.credibility is Credibility.CONFIRMED
        assert current.attributes["conflict_relevance"] == "unrelated"
    else:
        assert "conflict_screening" not in current.attributes
    if change not in {"target", "enrich"}:
        rig.bus.publish.assert_not_called()


async def test_call_budget_batch_bounds_failure_cooldown_and_hour_reset(rig):
    for index in range(15):
        rig.store.upsert(pair(str(index), title=f"Military forces exchange artillery fire {index}"))
    rig.model.screen.side_effect = RuntimeError("private upstream failure")
    assert await rig.queue.run_once() == 0 and rig.queue.state == "model_error"
    assert len(rig.model.screen.await_args.args[1]) == 10
    assert await rig.queue.run_once() == 0
    rig.clock.advance(timedelta(minutes=16))
    assert await rig.queue.run_once() == 0 and rig.queue.state == "budget_exhausted"
    assert rig.model.screen.await_count == 1
    rig.clock.advance(timedelta(hours=1))
    rig.model.screen.side_effect = lambda p, items: {
        item.key: ScreeningVerdict("uncertain", "Insufficient detail.", "") for item in items
    }
    assert await rig.queue.run_once() == 20
    assert rig.model.screen.await_count == 2 and rig.queue.calls_this_hour == 1


async def test_stop_cancels_call_without_publishing_or_leaking_task(rig):
    rig.store.upsert(pair())
    entered = asyncio.Event()

    async def screen(p, items):
        entered.set()
        await asyncio.Event().wait()

    rig.model.screen.side_effect = screen
    await rig.queue.start()
    await rig.queue.start()
    await entered.wait()
    await rig.queue.stop()
    await rig.queue.stop()
    assert rig.queue.calls_this_hour == 1 and not rig.queue._busy
    rig.bus.publish.assert_not_called()


async def test_full_attributes_are_preserved_instead_of_silently_truncated(rig):
    source, target = pair()
    target = target.with_changes(attributes={str(i): i for i in range(40)})
    rig.store.upsert([source, target])
    await rig.queue.run_once()
    assert rig.store.get(target.id).attributes == target.attributes


async def test_rejected_source_can_be_rescreened_after_global_model_change(rig):
    source, target = pair()
    rig.store.upsert([source, target])
    rig.model.screen.side_effect = lambda p, items: {
        item.key: ScreeningVerdict("unrelated", "No armed conflict.", "") for item in items
    }
    assert await rig.queue.run_once() == 2
    rig.runtime.generation = ScreeningGeneration("two", profile("second"))
    rig.clock.advance(timedelta(hours=1))
    assert await rig.queue.run_once() == 2
    assert rig.model.screen.await_count == 2
    assert rig.store.get(source.id).attributes["conflict_screening_model"] == "second"


async def test_delayed_grading_keeps_screening_translation_and_drops_stale_snapshots():
    store = InMemoryEventStore()
    source, original = pair()
    current = original.with_changes(
        title_en="Translated", attributes={"conflict_relevance": "unrelated"}
    )
    store.upsert([current, source.with_changes(content_hash="updated")])
    graded = original.with_changes(
        credibility=Credibility.CANNOT_BE_JUDGED, grade_rationale="New grade"
    )
    await store.put_grades_cooperatively([graded, source, make_event("removed")])
    stored = store.get(original.id)
    assert stored.title_en == "Translated" and stored.attributes == current.attributes
    assert stored.credibility is Credibility.CANNOT_BE_JUDGED
    assert store.get(source.id).content_hash == "updated"
    assert store.get(make_event("removed").id) is None
