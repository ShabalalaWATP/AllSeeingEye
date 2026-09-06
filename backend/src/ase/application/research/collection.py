"""Bounded collection with safe failures and truthful per-provider receipts."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from math import isfinite

from ase.application.ports.research import ResearchProvider
from ase.application.research.planning import build_plan
from ase.domain.events import Event
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchMode,
    ResearchQuery,
)

Progress = Callable[[CollectionAttempt], Awaitable[None]]
CURRENT_RECORDS = frozenset(
    {
        "current_dns_snapshot",
        "current_registry_snapshot",
        "current_directory_snapshot",
        "current_certificate_snapshot",
    }
)


@dataclass(frozen=True, slots=True)
class CollectionBudget:
    requests: int
    seconds: float
    per_request_seconds: float
    items: int

    def __post_init__(self) -> None:
        if not 1 <= self.requests <= 32 or not 1 <= self.items <= 1000:
            raise ValueError("Invalid collection request or item budget")
        if (
            any(
                not isfinite(value) or value <= 0
                for value in (self.seconds, self.per_request_seconds)
            )
            or self.seconds > 300
            or self.per_request_seconds > 60
        ):
            raise ValueError("Invalid collection deadline")

    @classmethod
    def for_mode(cls, mode: ResearchMode) -> CollectionBudget:
        if mode == ResearchMode.DETAILED:
            return cls(requests=24, seconds=180, per_request_seconds=20, items=800)
        return cls(requests=6, seconds=45, per_request_seconds=12, items=200)


class ResearchCollector:
    """Collect privately without touching the shared store or holding database locks.

    Provider instances represent a single request (including a specific language).
    Serial admission avoids an unbounded task queue and keeps cancellation direct.
    Output dates are publication dates; this does not establish event-time coverage.
    """

    def __init__(self, providers: Sequence[ResearchProvider]) -> None:
        if len(providers) > 64 or len({provider.id for provider in providers}) != len(providers):
            raise ValueError("Provide at most 64 uniquely identified collection providers")
        self._providers = tuple(providers)

    async def collect(
        self,
        query: ResearchQuery,
        *,
        budget: CollectionBudget | None = None,
        progress: Progress | None = None,
    ) -> ResearchBatch:
        limits = budget or CollectionBudget.for_mode(query.mode)
        plan = build_plan(
            query,
            self._providers,
            requests=limits.requests,
            seconds=limits.seconds,
            items=limits.items,
        )
        deadline = asyncio.get_running_loop().time() + limits.seconds
        requests = 0
        items: dict[str, Event] = {}
        attempts: list[CollectionAttempt] = []
        for provider, task in zip(self._providers, plan.tasks, strict=True):
            if not task.selected:
                continue
            routed = replace(query, terms=task.terms)
            remaining = deadline - asyncio.get_running_loop().time()
            if not task.supported:
                attempt = self._receipt(
                    provider,
                    CollectionStatus.UNSUPPORTED,
                    "This source does not support the requested scope.",
                )
            elif requests >= limits.requests or remaining <= 0 or len(items) >= limits.items:
                attempt = self._receipt(
                    provider,
                    CollectionStatus.BUDGET_EXHAUSTED,
                    "The collection budget was reached before this request.",
                )
            else:
                requests += 1
                batch = await self._fetch(
                    provider, routed, min(remaining, limits.per_request_seconds)
                )
                eligible = not batch.attempts or batch.attempts[0].status in (
                    CollectionStatus.COMPLETED,
                    CollectionStatus.EMPTY,
                )
                retained = self._retain(batch.items if eligible else (), query, items, limits.items)
                attempt = self._summarise(provider, batch, retained)
            attempts.append(attempt)
            if progress is not None:
                await progress(attempt)
        return ResearchBatch(items=tuple(items.values()), attempts=tuple(attempts), plan=plan)

    @staticmethod
    async def _fetch(
        provider: ResearchProvider, query: ResearchQuery, seconds: float
    ) -> ResearchBatch:
        try:
            async with asyncio.timeout(seconds):
                batch = await provider.collect(query)
                if len(batch.attempts) > 1:
                    raise ValueError("A request must have a single coverage receipt")
                return batch
        except TimeoutError:
            status, explanation = CollectionStatus.TIMED_OUT, "The source exceeded its deadline."
        except Exception:
            # Never include upstream errors: they can contain queries, keys or source text.
            status, explanation = CollectionStatus.FAILED, "The source could not be collected."
        return ResearchBatch(attempts=(ResearchCollector._receipt(provider, status, explanation),))

    @staticmethod
    def _retain(
        incoming: tuple[Event, ...], query: ResearchQuery, items: dict[str, Event], limit: int
    ) -> int:
        added = 0
        for item in incoming:
            if len(items) >= limit:
                break
            if item.published_at.utcoffset() is None or (
                item.attributes.get("record_kind") not in CURRENT_RECORDS
                and not query.since <= item.published_at < query.until
            ):
                continue
            if item.id not in items:
                items[item.id] = item
                added += 1
        return added

    @staticmethod
    def _receipt(
        provider: ResearchProvider, status: CollectionStatus, explanation: str, count: int = 0
    ) -> CollectionAttempt:
        return CollectionAttempt(provider.id, provider.name, status, count, explanation)

    @staticmethod
    def _summarise(
        provider: ResearchProvider, batch: ResearchBatch, retained: int
    ) -> CollectionAttempt:
        if batch.attempts:
            first = batch.attempts[0]
            if first.status not in (CollectionStatus.COMPLETED, CollectionStatus.EMPTY):
                return CollectionAttempt(
                    provider.id, provider.name, first.status, 0, first.explanation, first.language
                )
            explanation = first.explanation
            language = first.language
        else:
            explanation, language = "", None
        status = CollectionStatus.COMPLETED if retained else CollectionStatus.EMPTY
        if batch.items and not retained:
            explanation = (
                "No additional items within the requested publication period. " + explanation
            )
        if any(item.attributes.get("record_kind") in CURRENT_RECORDS for item in batch.items):
            explanation = (
                "Includes current observed records as context, not historical-window evidence. "
                + explanation
            )
        return CollectionAttempt(
            provider.id, provider.name, status, retained, explanation[:1000], language
        )
