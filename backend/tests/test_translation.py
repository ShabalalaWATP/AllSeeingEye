"""Translation: the queue over the live store and the LLM translator behind a profile role."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.translate import TranslatorUnavailable
from ase.application.translate.queue import TranslationQueue, needs_translation
from feeds_helpers import FakeClock, make_event

NOW = datetime(2026, 9, 5, 23, 0, tzinfo=UTC)


class FakeTranslator:
    def __init__(self, *, available: bool = True) -> None:
        self.batches: list[list[tuple[str, str]]] = []
        self.available = available

    async def translate(self, items: Sequence[tuple[str, str]]) -> list[str | None]:
        if not self.available:
            raise TranslatorUnavailable("no profile")
        self.batches.append(list(items))
        return [None if text.startswith("skip") else f"EN: {text}" for text, _lang in items]


def foreign(event_id: str, title: str, language: str = "uk", **overrides: object):
    return replace(
        make_event(event_id, title=title, published_at=NOW - timedelta(hours=1), **overrides),  # type: ignore[arg-type]
        language=language,
    )


async def test_queue_translates_once_caches_and_keeps_a_budget() -> None:
    store = InMemoryEventStore()
    bus = InMemoryEventBus()
    same = "Ракетний удар по Києву"
    a, b = foreign("a", same), foreign("b", same)
    skipped = foreign("c", "skip це")
    french = foreign("d", "Frappes sur Kyiv", language="fr")
    english = replace(make_event("e", title="English already"), language="en")
    unknown = replace(make_event("f", title="Unknown tongue"), language="und")
    store.upsert([a, b, skipped, french, english, unknown])
    assert (
        needs_translation(a) and not needs_translation(english) and not needs_translation(unknown)
    )

    translator = FakeTranslator()
    queue = TranslationQueue(store, bus, translator, FakeClock(NOW), batch=3, calls_per_hour=1)
    subscription = bus.subscribe()
    assert await queue.run_once() == 2
    message = await anext(aiter(subscription))
    assert message.kind == "event.upsert" and message.payload["source_id"] == "translation"
    stored = lambda event: store.get(event.id)  # noqa: E731
    assert (stored(a) or a).title_en == f"EN: {same}"
    assert (stored(b) or b).title_en == f"EN: {same}"  # the second copy came from the cache
    assert (stored(skipped) or skipped).title_en is None
    assert len(translator.batches) == 1 and len(translator.batches[0]) == 2
    assert queue.calls_this_hour == 1

    assert await queue.run_once() == 0  # French is pending but the hourly budget is spent
    assert len(translator.batches) == 1
    later = TranslationQueue(store, bus, translator, FakeClock(NOW + timedelta(hours=1)), batch=3)
    assert await later.run_once() == 1
    assert (stored(french) or french).title_en == "EN: Frappes sur Kyiv"
    assert await later.run_once() == 0
    subscription.close()


async def test_queue_waits_when_no_translator_is_available() -> None:
    store = InMemoryEventStore()
    event = foreign("a", "Ракетний удар по Києву")
    store.upsert([event])
    queue = TranslationQueue(
        store, InMemoryEventBus(), FakeTranslator(available=False), FakeClock(NOW)
    )
    assert await queue.run_once() == 0
    assert queue.calls_this_hour == 0
    assert (store.get(event.id) or event).title_en is None
