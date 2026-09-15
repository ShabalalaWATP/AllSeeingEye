"""Frozen routed tasks meet current source admission without spending challenge slots."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import pytest

from ase.application.research.allocated_plan import allocate_plan_tasks
from ase.application.research.budget import CollectionBudget
from ase.application.research.planning import build_plan
from ase.application.research.source_allocation_types import AllocationProfile
from ase.application.source_capabilities import CapabilityReadiness, ResolvedCapability
from ase.container.research_allocation import ResearchAllocationContext
from ase.domain.research import ResearchMode, ResearchQuery
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_plan import QueryVariant, ResearchPlan
from ase.domain.research_tasks import PlannedQueryTask
from ase.domain.source_capabilities import (
    CapabilityScope,
    CapabilitySupport,
    ContentCapability,
    DateSupport,
    ExecutionRoute,
    LanguageSupport,
    SourceCapability,
)

NOW = datetime(2026, 9, 14, tzinfo=UTC)
REQUIREMENTS = (IntelligenceRequirement("drone", "Drone policy changes"),)


@dataclass
class Provider:
    id: str
    language: str = "en"
    name: str = "Fixture source"
    supports_planned_terms: bool = True
    only_terms: tuple[str, ...] | None = None

    def supports(self, query: ResearchQuery) -> bool:
        return self.only_terms is None or query.terms == self.only_terms


def _query(
    *, mode: ResearchMode = ResearchMode.QUICK, tasks: tuple[PlannedQueryTask, ...] = ()
) -> ResearchQuery:
    return ResearchQuery(
        "What changed in drone policy?",
        NOW - timedelta(days=7),
        NOW,
        languages=("en", "fr"),
        terms=("drone policy",),
        mode=mode,
        query_variants=(QueryVariant("fr", ("politique des drones",)),),
        planned_tasks=tasks,
    )


def _context(
    providers: tuple[Provider, ...], *, disabled: frozenset[str] = frozenset()
) -> ResearchAllocationContext:
    support = CapabilitySupport(
        (CapabilityScope.TOPIC,),
        (DateSupport.PUBLICATION_INTERVAL,),
        ("en", "fr"),
        LanguageSupport.NOT_FILTERED,
        "Fixture topic support only.",
    )
    resolved = tuple(
        ResolvedCapability(
            SourceCapability(
                provider.id,
                provider.name,
                "structured_data",
                ExecutionRoute.PUBLIC_RESEARCH,
                ContentCapability.STRUCTURED,
                support,
                provider.id,
                ("Fixture records only.",),
            ),
            CapabilityReadiness.DISABLED
            if provider.id in disabled
            else CapabilityReadiness.PUBLIC_UNVERIFIED,
        )
        for provider in providers
    )
    return ResearchAllocationContext(
        resolved,
        frozenset(provider.id for provider in providers if provider.id not in disabled),
        {
            provider.id: AllocationProfile(
                ("drone", "policy"), "Reviewed fixture profile", primary_content=True
            )
            for provider in providers
        },
    )


def _build(
    query: ResearchQuery, providers: tuple[Provider, ...]
) -> tuple[ResearchAllocationContext, ResearchPlan]:
    budget = CollectionBudget.for_initial_mode(query.mode)
    plan = build_plan(
        query,
        providers,
        requests=budget.requests,
        seconds=budget.seconds,
        items=budget.items,
    )
    return _context(providers), plan


def test_exact_variant_and_supplementary_tasks_survive_ranked_admission() -> None:
    tasks = (
        PlannedQueryTask("contrary", "alpha", "challenge", ("contrary drone claim",)),
        PlannedQueryTask("impact", "alpha", "challenge", ("drone policy impact",)),
    )
    query = _query(tasks=tasks)
    providers = (Provider("alpha", "fr"), Provider("bravo"), Provider("charlie"))
    context, plan = _build(query, providers)
    result = allocate_plan_tasks(query, plan, REQUIREMENTS, context, max_operations=3)
    assert result.frozen_plan is plan
    assert result.planned_operations == 3
    assert result.phases.initial_operations == 3
    assert result.phases.challenge_operations == 0
    assert len(result.baseline_allocation.provider_ids) == 1
    baseline, contrary, impact = result.admitted_tasks
    assert baseline is next(task for task in plan.tasks if task.task_id == "source:alpha")
    assert baseline.terms == ("politique des drones",)
    assert baseline.query_variant is query.query_variants[0]
    assert (contrary.task_id, impact.task_id) == ("operator:contrary", "operator:impact")
    assert (contrary.terms, impact.terms) == (
        ("contrary drone claim",),
        ("drone policy impact",),
    )
    assert all(task.supported and task.selected for task in result.admitted_tasks)
    receipts = {row.task_id: row for row in result.task_receipts}
    assert set(receipts) == {task.task_id for task in plan.tasks}
    assert receipts["source:bravo"].disposition == "budgeted"
    assert receipts["source:bravo"].reasons == ("initial_operation_cap",)
    reversed_context = replace(context, resolved=tuple(reversed(context.resolved)))
    assert result == allocate_plan_tasks(
        query, plan, REQUIREMENTS, reversed_context, max_operations=3
    )


@pytest.mark.parametrize(
    "mode,total,challenge",
    [(ResearchMode.DETAILED, 6, 4), (ResearchMode.ADVANCED, 8, 6)],
)
def test_supplementary_initial_task_does_not_double_reserve_post_draft_challenge(
    mode: ResearchMode, total: int, challenge: int
) -> None:
    tasks = (
        PlannedQueryTask("first", "alpha", "challenge", ("first drone policy",)),
        PlannedQueryTask("second", "alpha", "challenge", ("second drone policy",)),
    )
    query = _query(mode=mode, tasks=tasks)
    context, plan = _build(query, (Provider("alpha"), Provider("bravo")))
    result = allocate_plan_tasks(query, plan, REQUIREMENTS, context, max_operations=total)
    assert result.phases.initial_operations == 2
    assert result.phases.challenge_operations == challenge
    assert result.planned_operations == 2
    assert result.planned_operations + result.phases.challenge_operations == total
    assert result.baseline_allocation.phases.challenge_operations == challenge
    assert sum(row.disposition == "budgeted" for row in result.task_receipts) == 2
    uncapped = allocate_plan_tasks(query, plan, REQUIREMENTS, context)
    assert uncapped.phases.initial_operations == CollectionBudget.for_initial_mode(mode).requests
    assert uncapped.phases.challenge_operations == challenge
    assert uncapped.planned_operations + challenge <= CollectionBudget.for_mode(mode).requests


def test_disabled_and_exactly_unsupported_tasks_have_safe_exclusion_receipts() -> None:
    private = "PRIVATE_SENTINEL contrary terms"
    query = _query(tasks=(PlannedQueryTask("private", "alpha", "challenge", (private,)),))
    providers = (Provider("alpha"), Provider("bravo", only_terms=("unrelated",)))
    _, plan = _build(query, providers)
    result = allocate_plan_tasks(
        query, plan, REQUIREMENTS, _context(providers, disabled=frozenset({"alpha"}))
    )
    receipts = {row.task_id: row for row in result.task_receipts}
    assert receipts["source:alpha"].disposition == "excluded"
    assert "disabled" in receipts["source:alpha"].reasons
    assert "disabled" in receipts["operator:private"].reasons
    assert receipts["source:bravo"].reasons == ("exact_task_support_missing",)
    assert result.admitted_tasks == ()
    assert private not in repr(result.task_receipts)


def test_explicit_task_can_use_a_provider_with_unsupported_baseline_route() -> None:
    task = PlannedQueryTask("target", "alpha", "challenge", ("target drone policy",))
    query = _query(tasks=(task,))
    providers = (Provider("alpha", only_terms=task.terms),)
    context, plan = _build(query, providers)
    result = allocate_plan_tasks(query, plan, REQUIREMENTS, context, max_operations=1)
    assert tuple(task.task_id for task in result.admitted_tasks) == ("operator:target",)
    assert result.task_receipts[0].reasons == ("exact_task_support_missing",)
    assert result.task_receipts[1].disposition == "planned"


def test_stale_or_mismatched_frozen_plan_fails_closed() -> None:
    query = _query()
    providers = (Provider("alpha"),)
    context, plan = _build(query, providers)
    with pytest.raises(ValueError, match="authorised query"):
        allocate_plan_tasks(query, replace(plan, question="Other question"), REQUIREMENTS, context)
    with pytest.raises(ValueError, match="catalogue"):
        allocate_plan_tasks(query, plan, REQUIREMENTS, replace(context, resolved=()))
    with pytest.raises(ValueError, match="catalogue"):
        allocate_plan_tasks(query, replace(plan, tasks=plan.tasks * 2), REQUIREMENTS, context)
    with pytest.raises(ValueError, match="operation limit"):
        allocate_plan_tasks(query, plan, REQUIREMENTS, context, max_operations=True)
