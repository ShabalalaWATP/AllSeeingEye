"""At most two private collection passes share one admitted run and frozen inventory."""

import asyncio
from collections.abc import Sequence
from dataclasses import replace

from ase.application.ports.research import ReplanCallback, ResearchProvider
from ase.application.research.collection import (
    CollectionBudget,
    CollectionRunBudget,
    ResearchCollector,
)
from ase.application.research.planning import build_plan
from ase.domain.research import CollectionPass, CollectionStatus, ResearchBatch, ResearchQuery
from ase.domain.research_plan import ResearchPlan

_PLACEHOLDERS = frozenset({CollectionStatus.BUDGET_EXHAUSTED, CollectionStatus.UNSUPPORTED})
_SEARCHED = frozenset({CollectionStatus.EMPTY, CollectionStatus.COMPLETED})


def _remaining(state: CollectionRunBudget) -> bool:
    return (
        state.remaining_requests > 0 and state.remaining_items > 0 and state.remaining_seconds > 0
    )


def _effective_terms(plan: ResearchPlan | None) -> dict[str, tuple[str, ...]]:
    return (
        {task.source_id: task.terms for task in plan.tasks if task.selected and task.supported}
        if plan is not None
        else {}
    )


def _merge(
    first: ResearchBatch,
    query: ResearchQuery,
    invoked: bool,
    second: ResearchBatch | None = None,
    revised: ResearchQuery | None = None,
) -> ResearchBatch:
    attempts = {row.source_id: row for row in first.attempts}
    passes = [CollectionPass(query.terms, first.attempts, first.plan)]
    if second is not None:
        for row in second.attempts:
            previous = attempts.get(row.source_id)
            # Reservations and unsupported tasks cannot erase an actual earlier search.
            if (
                previous is None
                or row.status not in _PLACEHOLDERS
                or previous.status in _PLACEHOLDERS
            ):
                attempts[row.source_id] = row
        second_plan = second.plan
        if second_plan is not None and revised is not None and revised != query:
            second_plan = replace(second_plan, replans=1)
        passes.append(CollectionPass((revised or query).terms, second.attempts, second_plan))
    return ResearchBatch(
        items=first.items + (second.items if second else ()),
        attempts=tuple(attempts.values()),
        plan=replace(
            first.plan, replans=int(invoked), model_calls=first.plan.model_calls + int(invoked)
        )
        if first.plan is not None
        else None,
        passes=tuple(passes),
    )


async def collect_with_replan(
    providers: Sequence[ResearchProvider], query: ResearchQuery, replan: ReplanCallback
) -> ResearchBatch:
    """The caller retains shared service admission throughout both passes and the callback.

    Only empty successful searches justify a replan. Invalid, failed or declined
    suggestions retain the original query and use unattempted sources. A model
    cannot widen the operator's source selection, temporal, language or subject scope.
    """
    collector = ResearchCollector(providers)
    state = CollectionRunBudget(CollectionBudget.for_mode(query.mode))
    first = await collector.collect(
        query, run_budget=state, request_allowance=max(1, state.limits.requests // 2)
    )
    if not _remaining(state):
        return _merge(first, query, False)
    invoked = False
    revised: ResearchQuery | None = None
    changed_sources: frozenset[str] = frozenset()
    if not first.items and any(row.status in _SEARCHED for row in first.attempts):
        invoked = True
        try:
            async with asyncio.timeout(state.remaining_seconds):
                candidate = await replan(query, first, state.remaining_seconds)
            if (
                isinstance(candidate, ResearchQuery)
                and replace(candidate, terms=query.terms, query_variants=query.query_variants)
                == query
            ):
                candidate_plan = build_plan(
                    candidate,
                    providers,
                    requests=state.limits.requests,
                    seconds=state.limits.seconds,
                    items=state.limits.items,
                )
                original_terms = _effective_terms(first.plan)
                changed_sources = frozenset(
                    source_id
                    for source_id, terms in _effective_terms(candidate_plan).items()
                    if original_terms.get(source_id) != terms
                )
                if changed_sources:
                    revised = candidate
        except Exception:
            # Never persist model/provider errors, which can contain private text or keys.
            # CancelledError is a BaseException and must propagate to release admission.
            revised = None
    if not _remaining(state):
        return _merge(first, query, invoked)
    attempted = frozenset(
        row.source_id for row in first.attempts if row.status not in _PLACEHOLDERS
    )
    # A base-term edit may have no effect on a source with an operator-supplied
    # language variant. Spend the remaining allowance on changed or untried tasks.
    skip = attempted - changed_sources if revised is not None else attempted
    if first.plan is None or not any(
        task.selected and task.source_id not in skip for task in first.plan.tasks
    ):
        return _merge(first, query, invoked)
    second = await collector.collect(revised or query, run_budget=state, skip_source_ids=skip)
    return _merge(first, query, invoked, second, revised)
