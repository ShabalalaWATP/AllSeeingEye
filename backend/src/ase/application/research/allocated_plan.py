"""Bind a frozen provider plan to a current, bounded E01 source allocation.

This module changes no terms or task metadata. The caller must recheck current
source admission at dispatch and release, and enforce the returned phase limits.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from ase.application.research.budget import CollectionBudget
from ase.application.research.source_allocation_types import (
    DEPTH_CAPS,
    AllocationProfile,
    PhaseAllocation,
    SourceAllocation,
)
from ase.application.research.source_allocator import allocate_sources
from ase.application.source_capabilities import ResolvedCapability
from ase.domain.research import ResearchQuery
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_plan import ResearchPlan, ResearchTask
from ase.domain.research_tasks import task_identity
from ase.domain.source_capabilities import DateSupport


class AllocationContext(Protocol):
    """The public fields of a freshly resolved admission/profile snapshot."""

    @property
    def resolved(self) -> tuple[ResolvedCapability, ...]: ...

    @property
    def authorised_ids(self) -> frozenset[str]: ...

    @property
    def reviewed_profiles(self) -> Mapping[str, AllocationProfile]: ...


@dataclass(frozen=True, slots=True)
class TaskAllocationReceipt:
    task_id: str
    source_id: str
    purpose: str
    disposition: Literal["planned", "excluded", "budgeted"]
    reasons: tuple[str, ...]
    requirement_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AllocatedPlan:
    """Task receipts are authoritative; baseline allocation covers baseline slots only."""

    frozen_plan: ResearchPlan
    admitted_tasks: tuple[ResearchTask, ...]
    task_receipts: tuple[TaskAllocationReceipt, ...]
    baseline_allocation: SourceAllocation
    phases: PhaseAllocation

    @property
    def planned_operations(self) -> int:
        return len(self.admitted_tasks)


def _validate_frozen(query: ResearchQuery, plan: ResearchPlan, resolved_ids: set[str]) -> None:
    if (
        not isinstance(query, ResearchQuery)
        or not isinstance(plan, ResearchPlan)
        or plan.question != query.question
        or plan.since != query.since
        or plan.until != query.until
        or plan.languages != query.languages
        or plan.mode != query.mode.value
        or plan.focus != query.focus.value
        or plan.subject != query.subject
        or plan.country_isos != query.country_isos
        or plan.area != query.area
        or plan.time_basis != query.effective_time_basis
        or plan.research_web_search != query.research_web_search
        or plan.candidate_hypotheses != query.candidate_hypotheses
    ):
        raise ValueError("The frozen plan does not match its authorised query")
    baseline = {task.source_id: task for task in plan.tasks if task.purpose == "baseline"}
    if (
        len(baseline) != sum(task.purpose == "baseline" for task in plan.tasks)
        or set(baseline) != resolved_ids
        or any(task.task_id is None for task in plan.tasks)
        or len({task.task_id for task in plan.tasks}) != len(plan.tasks)
    ):
        raise ValueError("The frozen plan and resolved provider catalogue differ")
    for source_id, task in baseline.items():
        variant = task.query_variant
        if (
            task.task_id != "source:" + source_id
            or task.selected != (query.source_ids is None or source_id in query.source_ids)
            or (variant is not None and variant not in query.query_variants)
            or task.terms != (variant.terms if variant is not None else query.terms)
        ):
            raise ValueError("The frozen baseline task does not match the query")
    supplements = {task.task_id: task for task in plan.tasks if task.purpose != "baseline"}
    if set(supplements) != {task_identity(task) for task in query.planned_tasks}:
        raise ValueError("The frozen supplementary tasks do not match the query")
    for operator in query.planned_tasks:
        task = supplements[task_identity(operator)]
        if (
            operator.source_id not in baseline
            or task.source_id != operator.source_id
            or task.purpose != operator.purpose
            or task.terms != operator.terms
            or task.candidate_id != operator.candidate_id
            or task.selected != baseline[operator.source_id].selected
        ):
            raise ValueError("The frozen supplementary task changed")


def allocate_plan_tasks(
    query: ResearchQuery,
    frozen_plan: ResearchPlan,
    requirements: tuple[IntelligenceRequirement, ...],
    context: AllocationContext,
    *,
    accepted_dates: tuple[DateSupport, ...] = (DateSupport.PUBLICATION_INTERVAL,),
    max_operations: int | None = None,
) -> AllocatedPlan:
    """Admit exact routed tasks within initial slots, preserving challenge slots.

    Supplementary tasks consume initial operations, even when their purpose is a
    prewritten challenge. The post-draft challenge reserve is never spent here.
    An eligible baseline operation keeps one slot when explicit tasks compete.
    """
    resolved = context.resolved
    source_ids = {row.capability.id for row in resolved}
    _validate_frozen(query, frozen_plan, source_ids)
    policy_total, challenge_operations, *_ = DEPTH_CAPS[query.mode]
    initial_ceiling = CollectionBudget.for_initial_mode(query.mode).requests
    if (
        type(frozen_plan.request_limit) is not int
        or frozen_plan.request_limit < 0
        or (max_operations is not None and type(max_operations) is not int)
        or (max_operations is not None and not 0 <= max_operations <= policy_total)
    ):
        raise ValueError("Invalid frozen or requested operation limit")
    maximum = min(initial_ceiling, frozen_plan.request_limit) + challenge_operations
    if max_operations is not None:
        maximum = min(maximum, max_operations)
    baseline = {task.source_id: task for task in frozen_plan.tasks if task.purpose == "baseline"}
    any_support = {
        source_id: any(
            task.source_id == source_id and task.selected and task.supported
            for task in frozen_plan.tasks
        )
        for source_id in source_ids
    }
    eligibility = allocate_sources(
        query,
        requirements,
        resolved,
        authorised_ids=context.authorised_ids,
        provider_support=any_support,
        reviewed_profiles=context.reviewed_profiles,
        accepted_dates=accepted_dates,
        max_operations=maximum,
    )
    source_receipts = {receipt.source_id: receipt for receipt in eligibility.receipts}

    def eligible(task: ResearchTask) -> bool:
        return (
            task.selected
            and task.supported
            and source_receipts[task.source_id].disposition != "excluded"
        )

    supplements = tuple(
        task for task in frozen_plan.tasks if task.purpose != "baseline" and eligible(task)
    )
    has_baseline = any(eligible(task) for task in baseline.values())
    supplement_slots = min(
        len(supplements), max(0, eligibility.phases.initial_operations - int(has_baseline))
    )
    baseline_support = {
        source_id: task.selected and task.supported for source_id, task in baseline.items()
    }
    baseline_allocation = allocate_sources(
        query,
        requirements,
        resolved,
        authorised_ids=context.authorised_ids,
        provider_support=baseline_support,
        reviewed_profiles=context.reviewed_profiles,
        accepted_dates=accepted_dates,
        max_operations=maximum - supplement_slots,
    )
    admitted_baseline = tuple(baseline[key] for key in baseline_allocation.provider_ids)
    spare = max(
        0,
        eligibility.phases.initial_operations - len(admitted_baseline) - supplement_slots,
    )
    admitted = admitted_baseline + supplements[: supplement_slots + spare]
    planned_ids = {task.task_id for task in admitted}
    receipts = []
    for task in frozen_plan.tasks:
        source = source_receipts[task.source_id]
        reasons: tuple[str, ...]
        if task.task_id in planned_ids:
            disposition: Literal["planned", "excluded", "budgeted"] = "planned"
            reasons = ()
        elif not task.selected:
            disposition, reasons = "excluded", ("source_policy",)
        elif not task.supported:
            disposition, reasons = "excluded", ("exact_task_support_missing",)
        elif source.disposition == "excluded":
            disposition, reasons = "excluded", source.reasons
        else:
            disposition, reasons = "budgeted", ("initial_operation_cap",)
        if task.task_id is None:
            raise ValueError("Frozen task identity is required")
        receipts.append(
            TaskAllocationReceipt(
                task.task_id,
                task.source_id,
                task.purpose,
                disposition,
                reasons,
                source.requirement_ids,
            )
        )
    return AllocatedPlan(
        frozen_plan, admitted, tuple(receipts), baseline_allocation, eligibility.phases
    )
