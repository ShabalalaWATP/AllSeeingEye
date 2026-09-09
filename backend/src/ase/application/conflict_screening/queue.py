"""Bounded global screening outside ingestion, rendering and source-release locks."""

from __future__ import annotations

import asyncio
import contextlib
from collections import OrderedDict
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from ase.application.conflict_screening.inputs import Candidate, candidates, source_text
from ase.application.conflict_screening.model import LlmConflictScreener
from ase.application.conflict_screening.records import ScreeningVerdict
from ase.application.ports import Clock
from ase.application.ports.cooperative_feeds import CooperativeEventReader
from ase.application.ports.feeds import BusMessage, EventBus, EventQuery, EventStore
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.conflict_evidence import canonical_report_url
from ase.domain.events import Category, Event, freeze_attributes
from ase.domain.llm import LlmProfile

POLICY = "conflict-relevance-v1"
POOL = 5000
CACHE_SIZE = 2000
INTERVAL = 60


@dataclass(frozen=True)
class ScreeningGeneration:
    key: str
    profile: LlmProfile = field(repr=False)


class ScreeningRuntime(Protocol):
    async def resolve(self) -> ScreeningGeneration | None: ...
    def release(self, generation: ScreeningGeneration) -> AbstractAsyncContextManager[bool]: ...


class ConflictScreeningQueue:
    def __init__(
        self,
        store: EventStore,
        bus: EventBus,
        model: LlmConflictScreener,
        runtime: ScreeningRuntime,
        admission: SourceAdmission,
        clock: Clock,
        *,
        enabled: bool = True,
        calls_per_hour: int = 6,
    ) -> None:
        self._store, self._bus, self._model = store, bus, model
        self._runtime, self._admission, self._clock = runtime, admission, clock
        self._enabled, self._limit = enabled, calls_per_hour
        self._cache: OrderedDict[str, ScreeningVerdict] = OrderedDict()
        self._failures: OrderedDict[str, datetime] = OrderedDict()
        self._hour: datetime | None = None
        self.calls_this_hour = 0
        self.state = "waiting" if enabled else "disabled"
        self._task: asyncio.Task[None] | None = None
        self._busy = False

    async def run_once(self) -> int:
        if not self._enabled or self._busy:
            return 0
        self._busy = True
        try:
            return await self._cycle()
        finally:
            self._busy = False

    async def _cycle(self) -> int:
        now = self._clock.now()
        hour = now.replace(minute=0, second=0, microsecond=0)
        if self._hour != hour:
            self._hour, self.calls_this_hour = hour, 0
        generation = await self._runtime.resolve()
        if generation is None:
            self.state = "no_global_model"
            return 0
        query = EventQuery(
            categories=frozenset(
                {Category.CONFLICT, Category.NEWS, Category.POLITICAL, Category.HUMANITARIAN}
            ),
            limit=POOL,
        )
        pending = (
            await self._store.read_cooperatively(query, candidates)
            if isinstance(self._store, CooperativeEventReader)
            else candidates(self._store.query(query))
        )
        allowed = await self._admission.enabled_many(
            tuple(
                {
                    source
                    for candidate in pending
                    for source in (candidate.target.source_id, candidate.source.source_id)
                }
            )
        )
        batch, unique = self._batch(pending, allowed, generation, now)
        if not batch:
            self.state = "waiting_for_source_text"
            return 0
        if unique and self.calls_this_hour < self._limit:
            # Reserve before awaiting: failures/cancellation consume the call/output budget.
            self.calls_this_hour += 1
            try:
                results = await self._model.screen(
                    generation.profile, [item.text for item in unique.values()]
                )
            except Exception:
                for key in unique:
                    self._failures[key] = now
                self._bound(self._failures)
                self.state = "model_error"
                return await self._publish(batch, generation)
            async with self._runtime.release(generation) as current:
                if not current:
                    self.state = "model_changed"
                    return 0
                for key, candidate in unique.items():
                    verdict = results.get(candidate.text.key)
                    if verdict is not None:
                        self._cache[key] = verdict
                        self._cache.move_to_end(key)
                self._bound(self._cache)
        self.state = (
            "budget_exhausted" if unique and self.calls_this_hour >= self._limit else "ready"
        )
        return await self._publish(batch, generation)

    def _batch(
        self,
        pending: list[Candidate],
        allowed: dict[str, bool],
        generation: ScreeningGeneration,
        now: datetime,
    ) -> tuple[list[Candidate], dict[str, Candidate]]:
        batch: list[Candidate] = []
        unique: dict[str, Candidate] = {}
        for candidate in pending:
            if not all(
                allowed.get(source, False)
                for source in (candidate.target.source_id, candidate.source.source_id)
            ):
                continue
            key = f"{POLICY}:{generation.key}:{candidate.text.key}"
            if candidate.target.attributes.get("conflict_screening_key") == key:
                continue
            if key in self._failures and now - self._failures[key] < timedelta(minutes=15):
                continue
            if key not in self._cache and key not in unique and len(unique) >= 10:
                continue
            batch.append(candidate)
            if key not in self._cache:
                unique[key] = candidate
            if len(batch) == 100:
                break
        return batch, unique

    async def _publish(self, batch: list[Candidate], generation: ScreeningGeneration) -> int:
        async with self._runtime.release(generation) as released:
            if not released:
                return 0
            allowed = await self._admission.enabled_many(
                tuple(
                    {
                        source
                        for item in batch
                        for source in (item.target.source_id, item.source.source_id)
                    }
                )
            )
            changed: list[Event] = []
            for item in batch:
                key = f"{POLICY}:{generation.key}:{item.text.key}"
                verdict = self._cache.get(key)
                target, source = self._store.get(item.target.id), self._store.get(item.source.id)
                if (
                    verdict is None
                    or target is None
                    or source is None
                    or target.content_hash != item.target.content_hash
                    or source.content_hash != item.source.content_hash
                    or source_text(source) != item.text
                    or canonical_report_url(target.url) != canonical_report_url(item.target.url)
                    or canonical_report_url(source.url) != canonical_report_url(item.target.url)
                    or not allowed.get(target.source_id, False)
                    or not allowed.get(source.source_id, False)
                ):
                    continue
                metadata = {
                    "conflict_screening": "llm",
                    "conflict_relevance": verdict.relevance,
                    "conflict_screening_reason": verdict.reason,
                    "conflict_screening_quote": verdict.quote,
                    "conflict_screening_model": generation.profile.model,
                    "conflict_screening_provider": generation.profile.provider,
                    "conflict_screening_profile": str(generation.profile.id),
                    "conflict_screening_revision": generation.profile.revision,
                    "conflict_screening_source": source.source_id,
                    "conflict_screening_key": key,
                    "conflict_screening_at": self._clock.now().isoformat(),
                }
                # Do not discard existing source evidence to squeeze in enrichment metadata.
                attrs = dict(target.attributes) | metadata
                if len(attrs) <= 40:
                    changed.append(target.with_changes(attributes=freeze_attributes(attrs)))
            self._store.put(changed)
            retained = [
                event for item in changed if (event := self._store.get(item.id)) is not None
            ]
            if retained:
                await self._bus.publish(
                    BusMessage(
                        "event.upsert", {"source_id": "conflict_screening", "events": retained}
                    )
                )
            return len(retained)

    @staticmethod
    def _bound[T](cache: OrderedDict[str, T]) -> None:
        while len(cache) > CACHE_SIZE:
            cache.popitem(last=False)

    async def start(self) -> None:
        if self._enabled and self._task is None:
            self._task = asyncio.create_task(self._run(), name="conflict-screening")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception:
                # Do not log source text, prompts, provider responses or credentials.
                self.state = "unavailable"
            await asyncio.sleep(INTERVAL)
