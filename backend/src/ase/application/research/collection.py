"""Bounded collection with safe failures and truthful per-provider receipts."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace

from ase.application.ports.research import ResearchProvider
from ase.application.research.budget import CollectionBudget, CollectionRunBudget
from ase.application.research.planning import build_plan
from ase.domain.events import Event
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_matches_time, evidence_time
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchQuery,
)

__all__ = ["CollectionBudget", "CollectionRunBudget", "ResearchCollector"]

Progress = Callable[[CollectionAttempt], Awaitable[None]]
CURRENT_RECORDS = frozenset(
    {
        "current_dns_snapshot",
        "current_registry_snapshot",
        "current_directory_snapshot",
        "current_certificate_snapshot",
    }
)


class ResearchCollector:
    """Collect privately without touching the shared store or holding database locks.

    Provider instances represent a single request (including a specific language).
    Serial admission avoids an unbounded task queue and keeps cancellation direct.
    Area observations use acquisition dates; other records use publication dates.
    Neither establishes complete coverage of events in the requested interval.
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
        run_budget: CollectionRunBudget | None = None,
        request_allowance: int | None = None,
        skip_source_ids: frozenset[str] = frozenset(),
    ) -> ResearchBatch:
        """Return this pass's new items; a shared run budget prevents double admission."""
        if budget is not None and run_budget is not None:
            raise ValueError("Specify either a budget or an existing run budget")
        state = run_budget or CollectionRunBudget(budget or CollectionBudget.for_mode(query.mode))
        allowance = state.limits.requests if request_allowance is None else request_allowance
        if (
            isinstance(allowance, bool)
            or not isinstance(allowance, int)
            or not 0 <= allowance <= 32
        ):
            raise ValueError("A pass request allowance must be an integer from zero to 32")
        with state.pass_scope():
            return await self._collect(query, state, allowance, progress, skip_source_ids)

    async def _collect(
        self,
        query: ResearchQuery,
        state: CollectionRunBudget,
        allowance: int,
        progress: Progress | None,
        skip_source_ids: frozenset[str],
    ) -> ResearchBatch:
        limits = state.limits
        plan = build_plan(
            query,
            self._providers,
            requests=limits.requests,
            seconds=limits.seconds,
            items=limits.items,
        )
        requests = 0
        items: dict[str, Event] = {}
        attempts: list[CollectionAttempt] = []
        for provider, task in zip(self._providers, plan.tasks, strict=True):
            if not task.selected or provider.id in skip_source_ids:
                continue
            routed = replace(query, terms=task.terms)
            if not task.supported:
                attempt = self._receipt(
                    provider,
                    CollectionStatus.UNSUPPORTED,
                    "Area-based collection is unsupported for this request. "
                    + task.spatial_scope[:900]
                    if query.area is not None and not task.spatial_supported
                    else "This source does not support the requested scope.",
                )
            elif requests >= allowance or (seconds := state.admit()) is None:
                attempt = self._receipt(
                    provider,
                    CollectionStatus.BUDGET_EXHAUSTED,
                    "The collection run or pass budget was reached before this request.",
                )
            else:
                requests += 1
                batch = await self._fetch(provider, routed, seconds)
                eligible = not batch.attempts or batch.attempts[0].status in (
                    CollectionStatus.COMPLETED,
                    CollectionStatus.EMPTY,
                )
                retained = self._retain(batch.items if eligible else (), query, items, state)
                attempt = self._summarise(provider, batch, retained, query)
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
        incoming: tuple[Event, ...],
        query: ResearchQuery,
        items: dict[str, Event],
        state: CollectionRunBudget,
    ) -> int:
        added = 0
        for item in incoming:
            if state.remaining_items <= 0:
                break
            basis = query.effective_time_basis
            timestamp = evidence_time(item, basis)
            current_context = (
                query.area is None and item.attributes.get("record_kind") in CURRENT_RECORDS
            )
            if not (
                (current_context and timestamp is not None)
                or evidence_matches_time(item, basis, query.since, query.until)
            ):
                continue
            if state.retain(item.id):
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
        provider: ResearchProvider, batch: ResearchBatch, retained: int, query: ResearchQuery
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
                "No additional items within the requested "
                + (
                    "recorded"
                    if query.effective_time_basis is EvidenceTimeBasis.RECORDED
                    else "acquisition/publication"
                    if query.area
                    else "publication"
                )
                + " period. "
                + explanation
            )
        if query.effective_time_basis is EvidenceTimeBasis.RECORDED:
            explanation = (
                "Project years may only possibly overlap a narrower interval; "
                "unknown commitment years are excluded. " + explanation
            )
        if query.area and any(item.observation is not None for item in batch.items):
            explanation = (
                "Observations filtered by acquisition time, not retrieval time. " + explanation
            )
        if query.area is None and any(
            item.attributes.get("record_kind") in CURRENT_RECORDS for item in batch.items
        ):
            explanation = (
                "Includes current observed records as context, not historical-window evidence. "
                + explanation
            )
        return CollectionAttempt(
            provider.id, provider.name, status, retained, explanation[:1000], language
        )
