"""At most two private collection passes share one admitted run and frozen inventory."""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace

from ase.application.ports.research import (
    ContinuationProposal,
    ReplanCallback,
    ResearchProvider,
    SourceOperationCheckpoints,
)
from ase.application.reports.planning_deadlines import DURABLE_PLANNING_SECONDS
from ase.application.research.allocated_plan import AllocatedPlan
from ase.application.research.collection import (
    CollectionBudget,
    CollectionRunBudget,
    ResearchCollector,
)
from ase.application.research.continuation_review import unavailable, validate_proposal
from ase.application.research.planning import build_plan
from ase.domain.research import CollectionPass, CollectionStatus, ResearchBatch, ResearchQuery
from ase.domain.research_continuation import ContinuationTrace
from ase.domain.research_plan import ResearchPlan

_PLACEHOLDERS = frozenset(
    {
        CollectionStatus.BUDGET_EXHAUSTED,
        CollectionStatus.UNSUPPORTED,
        CollectionStatus.NOT_COLLECTED,
        CollectionStatus.UNAVAILABLE,
    }
)
# Unavailable is a placeholder for merging receipts, but may represent a real
# provider request. Do not dispatch that same query again just to fill pass two.
_UNATTEMPTED = _PLACEHOLDERS - {CollectionStatus.UNAVAILABLE}
_SEARCHED = frozenset({CollectionStatus.EMPTY, CollectionStatus.COMPLETED})
AllocationPlanner = Callable[[ResearchQuery], Awaitable[AllocatedPlan]]


def _remaining(state: CollectionRunBudget) -> bool:
    return (
        state.remaining_requests > 0 and state.remaining_items > 0 and state.remaining_seconds > 0
    )


def _effective_terms(
    plan: ResearchPlan | None, admitted_ids: frozenset[str] | None = None
) -> dict[str, tuple[tuple[str, ...], str | None]]:
    return (
        {
            (task.task_id or task.source_id): (
                task.terms,
                task.registry_lookup.subject if task.registry_lookup else None,
            )
            for task in plan.tasks
            if task.selected
            and task.supported
            and (admitted_ids is None or task.task_id in admitted_ids)
        }
        if plan is not None
        else {}
    )


def _merge(
    first: ResearchBatch,
    query: ResearchQuery,
    invoked: bool,
    second: ResearchBatch | None = None,
    revised: ResearchQuery | None = None,
    trace: ContinuationTrace | None = None,
) -> ResearchBatch:
    first_status = {(row.task_id or row.source_id): row.status for row in first.attempts}
    applied = (
        second is not None
        and revised is not None
        and any(
            row.status not in _PLACEHOLDERS
            and (
                _effective_terms(second.plan).get(row.task_id or row.source_id)
                != _effective_terms(first.plan).get(row.task_id or row.source_id)
                or first_status.get(row.task_id or row.source_id) not in _SEARCHED
            )
            for row in second.attempts
        )
    )
    if trace and trace.decision == "replan" and not applied:
        trace = replace(
            trace,
            decision="continue",
            override_reason="No revised search was admitted within the shared budget.",
        )
    attempts = {(row.task_id or row.source_id): row for row in first.attempts}
    passes = [CollectionPass(query.terms, first.attempts, first.plan)]
    if second is not None:
        for row in second.attempts:
            previous = attempts.get(row.task_id or row.source_id)
            # Reservations and unsupported tasks cannot erase an actual earlier search.
            # A failed second pass cannot hide first-pass items that remain admitted;
            # the per-pass receipts still record that second outcome.
            if (
                previous is None
                or previous.status in _PLACEHOLDERS
                or (
                    row.status not in _PLACEHOLDERS
                    and not (
                        previous.status is CollectionStatus.COMPLETED
                        and row.status is not CollectionStatus.COMPLETED
                    )
                )
            ):
                attempts[row.task_id or row.source_id] = row
        second_plan = second.plan
        if second_plan is not None and applied:
            second_plan = replace(second_plan, replans=1)
        passes.append(CollectionPass((revised or query).terms, second.attempts, second_plan))
    effective_plan = second.plan if applied and second is not None else first.plan
    return ResearchBatch(
        items=first.items + (second.items if second else ()),
        attempts=tuple(attempts.values()),
        plan=replace(
            effective_plan,
            replans=int(applied),
            model_calls=first.plan.model_calls + int(invoked),
            continuation=trace,
        )
        if effective_plan is not None and first.plan is not None
        else None,
        passes=tuple(passes),
        effective_query=revised if applied else query,
    )


async def collect_with_replan(  # noqa: PLR0912 - one shared-budget state machine
    providers: Sequence[ResearchProvider],
    query: ResearchQuery,
    replan: ReplanCallback,
    *,
    initial_budget: CollectionBudget | None = None,
    first_allocation: AllocatedPlan | None = None,
    allocate: AllocationPlanner | None = None,
    source_operations: SourceOperationCheckpoints | None = None,
) -> ResearchBatch:
    """The caller retains shared service admission throughout both passes and the callback.

    Empty searches or cited potential conflicts can justify one replan. Invalid, failed or declined
    suggestions retain the original query and use unattempted sources. A model
    cannot widen the operator's source selection, temporal, language or subject scope.
    """
    collector = ResearchCollector(providers)
    state = CollectionRunBudget(initial_budget or CollectionBudget.for_mode(query.mode))
    first = await collector.collect(
        query,
        run_budget=state,
        request_allowance=max(1, state.limits.requests // 2),
        allocated_plan=first_allocation,
        source_operations=source_operations,
        pass_index=1,
    )
    if not _remaining(state):
        return _merge(first, query, False)
    invoked = False
    revised: ResearchQuery | None = None
    changed_sources: frozenset[str] = frozenset()
    trace: ContinuationTrace | None = None
    if first.items or any(row.status in _SEARCHED for row in first.attempts):
        invoked = True
        try:
            # Model planning has its own bounded allowance. It does not consume
            # active source-acquisition time between the two collection passes.
            async with asyncio.timeout(DURABLE_PLANNING_SECONDS):
                candidate = await replan(query, first, DURABLE_PLANNING_SECONDS)
            if first.items and not isinstance(candidate, ContinuationProposal):
                candidate = ContinuationProposal(None, unavailable(first, ""))
            if isinstance(candidate, ContinuationProposal):
                invoked = candidate.model_called
                proposal = validate_proposal(candidate, query, first)
                trace = proposal.trace
                candidate = proposal.query if trace.decision == "replan" else None
                if trace.decision == "sufficient":
                    first = replace(
                        first,
                        attempts=tuple(
                            replace(
                                row,
                                status=CollectionStatus.NOT_COLLECTED,
                                explanation=(
                                    "Not collected after the model recommended stopping; "
                                    "coverage is incomplete."
                                ),
                            )
                            if row.status is CollectionStatus.BUDGET_EXHAUSTED
                            else row
                            for row in first.attempts
                        ),
                    )
                    return _merge(first, query, invoked, trace=trace)
            if (
                isinstance(candidate, ResearchQuery)
                and replace(candidate, terms=query.terms, query_variants=query.query_variants)
                == query
            ):
                candidate_allocation = await allocate(candidate) if allocate is not None else None
                candidate_plan = (
                    candidate_allocation.frozen_plan
                    if candidate_allocation is not None
                    else build_plan(
                        candidate,
                        providers,
                        requests=state.limits.requests,
                        seconds=state.limits.seconds,
                        items=state.limits.items,
                    )
                )
                original_ids = (
                    frozenset(
                        task.task_id
                        for task in first_allocation.admitted_tasks
                        if task.task_id is not None
                    )
                    if first_allocation is not None
                    else None
                )
                candidate_ids = (
                    frozenset(
                        task.task_id
                        for task in candidate_allocation.admitted_tasks
                        if task.task_id is not None
                    )
                    if candidate_allocation is not None
                    else None
                )
                original_terms = _effective_terms(first.plan, original_ids)
                changed_sources = frozenset(
                    source_id
                    for source_id, terms in _effective_terms(candidate_plan, candidate_ids).items()
                    if original_terms.get(source_id) != terms
                )
                if changed_sources:
                    revised = candidate
        except Exception:
            # Never persist model/provider errors, which can contain private text or keys.
            # CancelledError is a BaseException and must propagate to release admission.
            revised = None
            if first.items:
                trace = unavailable(first, "")
    if trace is not None and trace.decision == "replan" and revised is None:
        trace = replace(
            trace,
            decision="continue",
            override_reason="The proposed search did not change an eligible task in scope.",
        )
    if not _remaining(state):
        if trace and trace.decision == "replan":
            trace = replace(
                trace,
                decision="continue",
                override_reason="The shared collection budget expired before another search.",
            )
        return _merge(first, query, invoked, trace=trace)
    attempted = frozenset(
        (row.task_id or row.source_id) for row in first.attempts if row.status not in _UNATTEMPTED
    )
    # A base-term edit may have no effect on a source with an operator-supplied
    # language variant. Spend the remaining allowance on changed or untried tasks.
    skip = attempted - changed_sources if revised is not None else attempted
    if first.plan is None or not any(
        task.selected and (task.task_id or task.source_id) not in skip for task in first.plan.tasks
    ):
        return _merge(first, query, invoked, trace=trace)
    second_allocation = await allocate(revised or query) if allocate is not None else None
    second = await collector.collect(
        revised or query,
        run_budget=state,
        skip_task_ids=skip,
        allocated_plan=second_allocation,
        source_operations=source_operations,
        pass_index=2,
    )
    return _merge(first, query, invoked, second, revised, trace)
