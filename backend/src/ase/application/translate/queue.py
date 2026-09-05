"""The translation queue: every half minute, give a batch of foreign titles an English one.

Only events whose language is known and not English, and which have no English title yet,
are candidates. Each is tried once; a small cache keyed by language and title means a
story seen through several feeds costs one translation. An hourly call budget bounds what
a runaway feed can spend on the model.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime, timedelta

import structlog

from ase.application.ports import Clock
from ase.application.ports.feeds import BusMessage, EventBus, EventQuery, EventStore
from ase.application.ports.translate import Translator, TranslatorUnavailable
from ase.domain.events import Event

log = structlog.get_logger(__name__)

INTERVAL = timedelta(seconds=30)
LOOKBACK = timedelta(hours=24)
POOL = 2_000
BATCH = 20
CALLS_PER_HOUR = 60
CACHE_SIZE = 5_000
SKIP_LANGUAGES = frozenset({"en", "und", "mul", ""})
SleepFn = Callable[[float], Awaitable[None]]


def needs_translation(event: Event) -> bool:
    return event.language.lower() not in SKIP_LANGUAGES and event.title_en is None


class TranslationQueue:
    def __init__(
        self,
        store: EventStore,
        bus: EventBus,
        translator: Translator,
        clock: Clock,
        *,
        batch: int = BATCH,
        calls_per_hour: int = CALLS_PER_HOUR,
        interval: timedelta = INTERVAL,
        sleep: SleepFn = asyncio.sleep,
    ) -> None:
        self._store = store
        self._bus = bus
        self._translator = translator
        self._clock = clock
        self._batch = batch
        self._calls_per_hour = calls_per_hour
        self._interval = interval
        self._sleep = sleep
        self._tried: set[str] = set()
        self._cache: OrderedDict[tuple[str, str], str] = OrderedDict()
        self._hour: datetime | None = None
        self._calls = 0
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    @property
    def calls_this_hour(self) -> int:
        return self._calls

    def _budget_left(self, now: datetime) -> bool:
        hour = now.replace(minute=0, second=0, microsecond=0)
        if hour != self._hour:
            self._hour = hour
            self._calls = 0
        return self._calls < self._calls_per_hour

    def _remember(self, key: tuple[str, str], text: str) -> None:
        self._cache[key] = text
        self._cache.move_to_end(key)
        while len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)

    async def run_once(self) -> int:
        """Translate one batch; the number of events that gained an English title."""
        now = self._clock.now()
        pool = self._store.query(EventQuery(since=now - LOOKBACK, limit=POOL))
        candidates = [e for e in pool if needs_translation(e) and e.id not in self._tried]
        if not candidates:
            return 0
        batch = candidates[: self._batch]
        updated: list[Event] = []
        pending: list[Event] = []
        for event in batch:
            cached = self._cache.get((event.language.lower(), event.title))
            if cached is not None:
                updated.append(replace(event, title_en=cached))
                self._tried.add(event.id)
            else:
                pending.append(event)
        if pending and self._budget_left(now):
            updated.extend(await self._translate(pending))
        if updated:
            # put, not upsert: the content hash is unchanged, only the English title is new.
            self._store.put(updated)
            await self._bus.publish(
                BusMessage("event.upsert", {"source_id": "translation", "events": updated})
            )
        return len(updated)

    async def _translate(self, pending: list[Event]) -> list[Event]:
        """One call for the batch; repeated titles inside it are translated once."""
        unique: list[tuple[str, str]] = []
        seen: dict[tuple[str, str], int] = {}
        for event in pending:
            key = (event.language.lower(), event.title)
            if key not in seen:
                seen[key] = len(unique)
                unique.append((event.title, event.language.lower()))
        try:
            texts = await self._translator.translate(unique)
        except TranslatorUnavailable:
            return []
        self._calls += 1
        translated: list[Event] = []
        for event in pending:
            self._tried.add(event.id)
            key = (event.language.lower(), event.title)
            text = texts[seen[key]] if seen[key] < len(texts) else None
            if text:
                self._remember(key, text)
                translated.append(replace(event, title_en=text))
        return translated

    async def start(self) -> None:
        if self._task is None:
            self._stopping.clear()
            self._task = asyncio.create_task(self._run(), name="translation-queue")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.run_once()
            except Exception:
                log.exception("translation_cycle_failed")
            await self._sleep(self._interval.total_seconds())
