"""Catalogue and receipt metadata cannot enlarge operator or execution allowances."""

from dataclasses import replace

import pytest
from pydantic import ValidationError

from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_research_plan import ResearchPlanIn
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence
from ase.application.research.collection import CollectionBudget, ResearchCollector
from ase.application.research.model_planning import admit_proposals, planning_context
from ase.application.research.service import ResearchCollectionService
from ase.domain.research import (
    CollectionAttempt,
    CollectionPass,
    CollectionStatus,
    ResearchBatch,
    ResearchMode,
)
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from ase.domain.research_tasks import PlannedQueryTask
from test_operator_research_tasks import Provider
from test_research_collection import Provider as ItemProvider
from test_research_collection import event
from test_research_plan import QUERY


def inventory(count=128):
    return [Provider(f"source-{index}") for index in range(count)]


def tasks(count=8):
    return tuple(
        PlannedQueryTask(str(index), "source-0", "challenge", (f"explicit {index}",))
        for index in range(count)
    )


@pytest.mark.parametrize(
    "mode,requests,items", [("quick", 6, 200), ("detailed", 24, 800), ("advanced", 32, 1000)]
)
async def test_large_catalogue_preserves_actual_request_and_item_allowances(mode, requests, items):
    providers = inventory()
    query = replace(QUERY, mode=ResearchMode(mode))
    result = await ResearchCollector(providers).collect(query)
    assert len(result.attempts) == 128
    assert sum(len(provider.queries) for provider in providers) == requests
    assert result.plan.request_limit == requests and result.plan.item_limit == items
    assert (
        sum(row.status is CollectionStatus.BUDGET_EXHAUSTED for row in result.attempts)
        == 128 - requests
    )
    assert CollectionBudget.for_mode(query.mode).items == items


async def test_full_catalogue_and_eight_tasks_roundtrip_with_all_coverage_receipts():
    providers = inventory()
    query = replace(QUERY, planned_tasks=tasks())
    batch = await ResearchCollector(providers).collect(query)
    assert len(batch.plan.tasks) == len(batch.attempts) == 136
    assert sum(len(provider.queries) for provider in providers) == 6
    assert [row.task_id for row in batch.attempts[:4]] == [
        "source:source-0",
        "operator:0",
        "source:source-1",
        "operator:1",
    ]
    passes = (CollectionPass(query.terms, batch.attempts, batch.plan),)
    receipt = ResearchReceipt.build(query, batch.attempts, 0, batch.plan, passes)
    assert research_from_dict(research_to_dict(receipt)) == receipt

    for path in ("attempts", "plan", "passes"):
        damaged = research_to_dict(receipt)
        if path == "attempts":
            damaged["attempts"] = (*damaged["attempts"], damaged["attempts"][0])
        elif path == "plan":
            damaged["plan"]["tasks"] = (*damaged["plan"]["tasks"], damaged["plan"]["tasks"][0])
        else:
            damaged["passes"][0]["attempts"] = (
                *damaged["passes"][0]["attempts"],
                damaged["attempts"][0],
            )
        with pytest.raises(ValueError):
            research_from_dict(damaged)
    with pytest.raises(ValueError):
        ResearchBatch(attempts=(*batch.attempts, batch.attempts[0]))
    with pytest.raises(ValueError):
        replace(batch.plan, tasks=(*batch.plan.tasks, batch.plan.tasks[0]))


def test_catalogue_bound_and_explicit_selection_are_separate():
    providers = inventory()
    ResearchCollector(providers)
    with pytest.raises(ValueError):
        ResearchCollector(inventory(129))
    selected = tuple(provider.id for provider in providers[:64])
    query = replace(QUERY, source_ids=selected, planned_tasks=tasks())
    plan = ResearchCollectionService(lambda _: providers).plan(query)
    assert len(plan.tasks) == 136
    assert sum(row.selected for row in plan.tasks) == 72
    with pytest.raises(ValueError, match="64"):
        replace(query, source_ids=(*selected, providers[64].id))
    with pytest.raises(ValueError, match="eight"):
        replace(query, planned_tasks=tasks(9))
    with pytest.raises(ValidationError):
        ResearchPlanIn(
            question=QUERY.question,
            since=QUERY.since,
            until=QUERY.until,
            source_ids=[provider.id for provider in providers[:65]],
        )


def test_model_tasks_fit_large_catalogue_and_cannot_exceed_explicit_or_receipt_capacity():
    providers = inventory()
    service = ResearchCollectionService(lambda _: providers)
    query = replace(QUERY, source_ids=tuple(provider.id for provider in providers[:64]))
    context = planning_context(query, service.plan(query), 0)
    assert context["task_slots"] == 8
    proposals = tuple(replace(row, origin="model") for row in tasks())
    admitted = admit_proposals(query, context, (), proposals, service, 0)
    assert admitted.source_ids == query.source_ids and len(admitted.planned_tasks) == 8
    with pytest.raises(ValueError, match="selected task searches"):
        admit_proposals(
            query, context, (), (replace(proposals[0], source_id="source-127"),), service, 0
        )
    assert planning_context(admitted, service.plan(admitted), 0)["task_slots"] == 0
    with pytest.raises(ValueError):
        admit_proposals(
            query, context, (), (*proposals, replace(proposals[0], id="extra")), service, 0
        )

    automatic = replace(QUERY, source_ids=None)
    tight = planning_context(automatic, service.plan(automatic), 7)
    assert tight["task_slots"] == 1
    assert admit_proposals(automatic, tight, (), proposals[:1], service, 7).planned_tasks
    tight["task_slots"] = 8  # Admission independently checks the final receipt capacity.
    with pytest.raises(ValueError, match="receipt capacity"):
        admit_proposals(automatic, tight, (), proposals[:2], service, 7)


@pytest.mark.parametrize("mode,items", [("quick", 200), ("detailed", 800), ("advanced", 1000)])
async def test_large_catalogue_cannot_enlarge_retained_item_budget(mode, items):
    first = ItemProvider("first", ResearchBatch(items=tuple(event(str(i)) for i in range(1000))))
    remainder = [ItemProvider(f"other-{i}") for i in range(127)]
    batch = await ResearchCollector([first, *remainder]).collect(
        replace(QUERY, mode=ResearchMode(mode))
    )
    assert len(batch.items) == items and first.called == 1
    assert all(provider.called == 0 for provider in remainder)
    assert len(batch.attempts) == 128


async def test_large_catalogue_retains_unsupported_rows_without_spending_requests():
    providers = [ItemProvider(f"source-{i}", supported=i % 2 == 0) for i in range(128)]
    batch = await ResearchCollector(providers).collect(QUERY)
    assert len(batch.plan.tasks) == len(batch.attempts) == 128
    assert sum(row.status is CollectionStatus.UNSUPPORTED for row in batch.attempts) == 64
    assert sum(provider.called for provider in providers) == 6


async def test_retained_seed_and_large_public_catalogue_can_form_a_readable_report_receipt():
    providers = inventory()
    collection = ResearchCollectionService(lambda _: providers)
    retained = CollectionAttempt("retained", "Retained evidence", CollectionStatus.COMPLETED)
    _, receipt = await collect_report_evidence(
        QUERY,
        ReportRequest("ask"),
        collection,
        InMemoryEventStore,
        InMemoryEventStore(),
        seed_attempts=(retained,),
    )
    assert len(receipt.attempts) == 129 and receipt.attempts[0] == retained
    assert research_from_dict(research_to_dict(receipt)) == receipt
