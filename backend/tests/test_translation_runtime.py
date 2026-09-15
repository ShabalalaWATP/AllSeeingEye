"""Asynchronous enrichment preserves live-store freshness, budgets and shutdown."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.translate.queue import TranslationQueue
from ase.domain.events import Credibility
from ase.main import lifespan
from feeds_helpers import NOW, make_event
from helpers import FakeClock


@pytest.mark.parametrize("change", ["grade", "title", "language", "prune", "already"])
async def test_slow_translation_merges_only_onto_current_title(change: str) -> None:
    store = InMemoryEventStore()
    original = replace(make_event("a", title="Bonjour"), language="fr")
    store.upsert([original])
    entered, finish = asyncio.Event(), asyncio.Event()

    async def translate(items):
        entered.set()
        await finish.wait()
        return ["Hello"]

    translator = AsyncMock()
    translator.translate.side_effect = translate
    queue = TranslationQueue(store, InMemoryEventBus(), translator, FakeClock(NOW))
    task = asyncio.create_task(queue.run_once())
    await entered.wait()
    if change == "prune":
        store.prune(NOW + timedelta(days=60))
    else:
        changes = {
            "grade": {"credibility": Credibility.CONFIRMED},
            "title": {"title": "Bonsoir"},
            "language": {"language": "de"},
            "already": {"title_en": "Existing translation"},
        }
        store.put([replace(original, **changes[change])])
    finish.set()
    count = await task
    current = store.get(original.id)
    if change == "grade":
        assert count == 1 and current.title_en == "Hello"
        assert current.credibility is Credibility.CONFIRMED
    else:
        assert count == 0
        if change == "prune":
            assert current is None
        elif change == "already":
            assert current.title_en == "Existing translation"
        else:
            assert current.title_en is None


async def test_failures_consume_budget_and_same_queue_resets_next_hour() -> None:
    store = InMemoryEventStore()
    store.upsert([replace(make_event("a"), language="fr")])
    translator = AsyncMock()
    translator.translate.side_effect = RuntimeError("failed call")
    clock = FakeClock(NOW)
    queue = TranslationQueue(store, InMemoryEventBus(), translator, clock, calls_per_hour=1)
    with pytest.raises(RuntimeError):
        await queue.run_once()
    assert await queue.run_once() == 0 and queue.calls_this_hour == 1
    assert translator.translate.await_count == 1
    clock.advance(timedelta(hours=1))
    translator.translate.side_effect = None
    translator.translate.return_value = ["English"]
    assert await queue.run_once() == 1 and queue.calls_this_hour == 1


async def test_revised_failed_title_can_be_retried_and_old_attempts_are_pruned() -> None:
    store = InMemoryEventStore()
    event = replace(make_event("a"), language="fr")
    store.upsert([event])
    translator = AsyncMock()
    translator.translate.return_value = [None]
    queue = TranslationQueue(store, InMemoryEventBus(), translator, FakeClock(NOW))
    await queue.run_once()
    await queue.run_once()
    assert translator.translate.await_count == 1
    store.put([replace(event, title="Revised title")])
    await queue.run_once()
    assert translator.translate.await_count == 2
    store.prune(NOW + timedelta(days=60))
    await queue.run_once()
    assert len(queue._tried) == 0


async def test_enrichment_obeys_memory_budget_and_announces_expiry() -> None:
    store = InMemoryEventStore(memory_budget_bytes=600)
    event = replace(make_event("a"), language="fr")
    store.upsert([event])
    translator = AsyncMock()
    translator.translate.return_value = ["x" * 400]
    bus = AsyncMock()
    queue = TranslationQueue(store, bus, translator, FakeClock(NOW))
    assert await queue.run_once() == 0
    assert store.stats().estimated_bytes <= 600
    assert event.id in store.prune(NOW).ids
    bus.publish.assert_not_called()


async def test_stop_cancels_in_flight_call_without_writing_or_publishing() -> None:
    store = InMemoryEventStore()
    event = replace(make_event("a"), language="fr")
    store.upsert([event])
    entered = asyncio.Event()

    async def translate(items):
        entered.set()
        await asyncio.Event().wait()

    translator, bus = AsyncMock(), AsyncMock()
    translator.translate.side_effect = translate
    queue = TranslationQueue(store, bus, translator, FakeClock(NOW))
    await queue.start()
    await queue.start()
    await entered.wait()
    await queue.stop()
    await queue.stop()
    assert translator.translate.await_count == 1
    assert store.get(event.id).title_en is None
    bus.publish.assert_not_called()


@pytest.mark.parametrize("enabled", [False, True])
async def test_lifespan_controls_translation_before_disposal(app: FastAPI, monkeypatch, enabled):
    container = app.state.container
    container.settings.feeds_enabled = enabled
    jobs = [
        "scheduler",
        "aviation_monitor",
        "evaluator",
        "schedule_runner",
        "social_monitor",
        "translation_queue",
        "conflict_screening",
    ]
    mocks = []
    for name in jobs:
        job = AsyncMock()
        monkeypatch.setattr(container, name, job)
        mocks.append(job)
    async with lifespan(app):
        assert mocks[-1].start.await_count == int(enabled)
        assert mocks[jobs.index("schedule_runner")].start.await_count == 1
    mocks[-1].stop.assert_awaited_once()
    mocks[jobs.index("schedule_runner")].stop.assert_awaited_once()
