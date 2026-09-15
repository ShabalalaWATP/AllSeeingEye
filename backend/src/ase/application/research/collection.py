"""Bounded collection with safe failures and truthful per-provider receipts."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace

from ase.application.ports.research import ResearchProvider, SourceOperationCheckpoints
from ase.application.research.allocated_plan import AllocatedPlan, TaskAllocationReceipt
from ase.application.research.budget import CollectionBudget, CollectionRunBudget
from ase.application.research.phase_ledger import Phase
from ase.application.research.planning import build_plan
from ase.application.research.reserved_collection import (
    CURRENT_RECORDS,
    Freeze,
    eligible_for_query,
    fetch_reserved,
    source_item_key,
)
from ase.domain.events import Event
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchQuery,
)
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS, MAX_COLLECTION_REQUESTS
from ase.domain.research_plan import ResearchTask

__all__ = ["CollectionBudget", "CollectionRunBudget", "ResearchCollector"]

Progress = Callable[[CollectionAttempt], Awaitable[None]]


class ResearchCollector:
    """Collect bounded provider requests privately with serial admission.

    Date-filtered results cannot establish complete coverage of the requested interval."""

    def __init__(self, providers: Sequence[ResearchProvider]) -> None:
        if len(providers) > MAX_COLLECTION_PROVIDERS or len(
            {provider.id for provider in providers}
        ) != len(providers):
            raise ValueError(
                f"Provide at most {MAX_COLLECTION_PROVIDERS} "
                "uniquely identified collection providers"
            )
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
        skip_task_ids: frozenset[str] = frozenset(),
        allocated_plan: AllocatedPlan | None = None,
        source_operations: SourceOperationCheckpoints | None = None,
        pass_index: int = 1,
        phase: Phase = "initial",
        freeze: Freeze | None = None,
    ) -> ResearchBatch:
        """Return this pass's new items; a shared run budget prevents double admission."""
        if budget is not None and run_budget is not None:
            raise ValueError("Specify either a budget or an existing run budget")
        if type(pass_index) is not int or pass_index not in (1, 2):
            raise ValueError("A source pass must be the first or second collection pass")
        state = run_budget or CollectionRunBudget(budget or CollectionBudget.for_mode(query.mode))
        allowance = state.limits.requests if request_allowance is None else request_allowance
        if (
            isinstance(allowance, bool)
            or not isinstance(allowance, int)
            or not 0 <= allowance <= MAX_COLLECTION_REQUESTS
        ):
            raise ValueError(
                "A pass request allowance must be an integer "
                f"from zero to {MAX_COLLECTION_REQUESTS}"
            )
        with state.pass_scope():
            return await self._collect(
                query,
                state,
                allowance,
                progress,
                skip_source_ids,
                skip_task_ids,
                allocated_plan,
                source_operations,
                pass_index,
                phase,
                freeze,
            )

    async def _collect(  # noqa: PLR0912 - serial source admission and receipt state machine
        self,
        query: ResearchQuery,
        state: CollectionRunBudget,
        allowance: int,
        progress: Progress | None,
        skip_source_ids: frozenset[str],
        skip_task_ids: frozenset[str],
        allocated_plan: AllocatedPlan | None,
        source_operations: SourceOperationCheckpoints | None,
        pass_index: int,
        phase: Phase,
        freeze: Freeze | None,
    ) -> ResearchBatch:
        limits = state.limits
        if allocated_plan is None:
            plan = build_plan(
                query,
                self._providers,
                requests=limits.requests,
                seconds=limits.seconds,
                items=limits.items,
            )
            tasks = plan.tasks
            admitted_ids: frozenset[str] | None = None
            allocation_receipts: dict[str, TaskAllocationReceipt] = {}
        else:
            admitted_ids = frozenset(
                task.task_id for task in allocated_plan.admitted_tasks if task.task_id is not None
            )
            tasks = allocated_plan.admitted_tasks + tuple(
                task
                for task in allocated_plan.frozen_plan.tasks
                if task.task_id not in admitted_ids
            )
            plan = replace(allocated_plan.frozen_plan, tasks=tasks)
            allocation_receipts = {
                receipt.task_id: receipt for receipt in allocated_plan.task_receipts
            }
        requests = 0
        items: dict[str, Event] = {}
        attempts: list[CollectionAttempt] = []
        providers = {provider.id: provider for provider in self._providers}
        for task in tasks:
            provider = providers[task.source_id]
            if (
                not task.selected
                or provider.id in skip_source_ids
                or (task.task_id or task.source_id) in skip_task_ids
            ):
                continue
            if admitted_ids is not None and task.task_id not in admitted_ids:
                receipt = allocation_receipts.get(task.task_id or "")
                if receipt is None:
                    raise ValueError("The allocated plan lacks a frozen task receipt")
                attempt = self._allocation_receipt(provider, task, receipt)
                attempts.append(attempt)
                if progress is not None:
                    await progress(attempt)
                continue
            routed = replace(
                query,
                terms=task.terms,
                subject=task.registry_lookup.subject if task.registry_lookup else query.subject,
                query_variants=() if task.purpose != "baseline" else query.query_variants,
            )
            if not task.supported:
                attempt = self._receipt(
                    provider,
                    CollectionStatus.UNSUPPORTED,
                    "This source does not support explicit task terms. No task request was made."
                    if task.purpose != "baseline"
                    and not task.planned_terms_supported
                    and task.registry_lookup is None
                    else "Area-based collection is unsupported for this request. "
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
                if source_operations is not None:
                    reserved = await fetch_reserved(
                        provider,
                        task,
                        routed,
                        query,
                        seconds,
                        max_items=state.remaining_items,
                        seen_ids=frozenset(items),
                        source_operations=source_operations,
                        pass_index=pass_index,
                        phase=phase,
                        fetch=self._fetch,
                        freeze=freeze,
                    )
                    if reserved.batch is None:
                        attempt = self._receipt(provider, reserved.status, reserved.explanation)
                    else:
                        retained = self._retain(
                            tuple(
                                item
                                for item in reserved.batch.items
                                if source_item_key(item.id) in reserved.accepted_keys
                            ),
                            query,
                            items,
                            state,
                        )
                        attempt = self._summarise(provider, reserved.batch, retained, query)
                else:
                    batch = await self._fetch(provider, routed, seconds)
                    eligible = not batch.attempts or batch.attempts[0].status in (
                        CollectionStatus.COMPLETED,
                        CollectionStatus.EMPTY,
                    )
                    retained = self._retain(batch.items if eligible else (), query, items, state)
                    attempt = self._summarise(provider, batch, retained, query)
            attempt = replace(
                attempt,
                task_id=task.task_id,
                purpose=task.purpose,
                candidate_id=task.candidate_id,
                registry_lookup=task.registry_lookup,
                query_variant=task.query_variant,
            )
            attempts.append(attempt)
            if progress is not None:
                await progress(attempt)
        return ResearchBatch(items=tuple(items.values()), attempts=tuple(attempts), plan=plan)

    @staticmethod
    def _allocation_receipt(
        provider: ResearchProvider, task: ResearchTask, receipt: TaskAllocationReceipt
    ) -> CollectionAttempt:
        unavailable = {"disabled", "not_authorised", "requirement_missing", "requirement_unknown"}
        unsupported = {"unsupported_scope", "unsupported_language", "unsupported_dates"}
        status = (
            CollectionStatus.BUDGET_EXHAUSTED
            if receipt.disposition == "budgeted"
            else CollectionStatus.UNSUPPORTED
            if not task.supported or any(reason in unsupported for reason in receipt.reasons)
            else CollectionStatus.UNAVAILABLE
            if any(reason in unavailable for reason in receipt.reasons)
            else CollectionStatus.NOT_COLLECTED
        )
        return CollectionAttempt(
            provider.id,
            provider.name,
            status,
            explanation="Source allocation: " + ", ".join(receipt.reasons) + ".",
            task_id=task.task_id,
            purpose=task.purpose,
            candidate_id=task.candidate_id,
            registry_lookup=task.registry_lookup,
            query_variant=task.query_variant,
        )

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
            if not eligible_for_query(item, query):
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
