"""Authorised query scope and task admission remain intact during ranking."""

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence_with_query
from ase.domain.errors import InvalidRequest
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchFocus,
    ResearchMode,
    ResearchQuery,
)
from ase.domain.research_plan import ResearchPlan, ResearchTask
from ase.domain.research_records import ResearchReceipt
from feeds_helpers import NOW, make_event
from report_job_snapshot_helpers import fixture_job, private_job


def test_only_completed_admitted_supplementary_tasks_affect_ranking() -> None:
    request = ReportRequest(
        "ask", question="Zirconium", research_mode=ResearchMode.QUICK, research_terms=()
    )
    job = fixture_job(request)
    query = ResearchQuery("Zirconium", job.period_from, job.period_to)
    tasks = (
        ResearchTask(
            "admitted",
            "Admitted",
            True,
            True,
            "en",
            ("zirconium",),
            "operator_supplied_task",
            task_id="operator:T1",
            purpose="challenge",
        ),
        ResearchTask(
            "excluded",
            "Excluded",
            False,
            True,
            "en",
            ("stale",),
            "operator_supplied_task",
            task_id="operator:T2",
            purpose="challenge",
        ),
        ResearchTask(
            "failed",
            "Failed",
            True,
            True,
            "en",
            ("stale",),
            "operator_supplied_task",
            task_id="operator:T3",
            purpose="challenge",
        ),
    )
    plan = ResearchPlan(
        query.question, query.since, query.until, query.languages, tasks, 6, 45.0, 200
    )
    attempts = (
        CollectionAttempt(
            "admitted",
            "Admitted",
            CollectionStatus.COMPLETED,
            1,
            task_id="operator:T1",
            purpose="challenge",
        ),
        CollectionAttempt(
            "failed", "Failed", CollectionStatus.FAILED, task_id="operator:T3", purpose="challenge"
        ),
    )
    receipt = ResearchReceipt.build(query, attempts, 1, plan)
    store = InMemoryEventStore()
    store.upsert(
        (
            *(
                make_event(
                    f"stale-{index}", source_id=f"stale-{index}", title=f"Stale record {index}"
                )
                for index in range(30)
            ),
            make_event(
                "answer",
                source_id="answer",
                title="Zirconium answer",
                published_at=NOW - timedelta(hours=12),
            ),
        )
    )
    selection = select_for_job(store, {}, job, None, runtime_query=query, receipt=receipt)
    assert len(selection.items) == 24
    assert any(item.title == "Zirconium answer" for item in selection.items)


def test_relevance_cannot_override_authorised_country_or_period() -> None:
    request = ReportRequest(
        "ask",
        question="Zirconium",
        research_mode=ResearchMode.QUICK,
        research_terms=("zirconium",),
        country_iso="GB",
        research_since=NOW - timedelta(days=1),
        research_until=NOW,
    )
    job = fixture_job(request)
    query = ResearchQuery(
        "Zirconium", job.period_from, job.period_to, terms=("zirconium",), country_iso="GB"
    )
    store = InMemoryEventStore()
    store.upsert(
        (
            make_event(
                "eligible",
                title="Zirconium",
                country_iso="GB",
                published_at=NOW - timedelta(hours=1),
            ),
            make_event(
                "wrong-country",
                title="Zirconium",
                country_iso="US",
                published_at=NOW - timedelta(hours=1),
            ),
            make_event(
                "old", title="Zirconium", country_iso="GB", published_at=NOW - timedelta(days=2)
            ),
        )
    )
    selected = select_for_job(store, {}, job, None, runtime_query=query)
    assert [item.title for item in selected.items] == ["Zirconium"]
    assert selected.considered == 1


async def test_private_input_never_becomes_public_collection_or_ranking_context() -> None:
    job = private_job()
    live = InMemoryEventStore()
    live.upsert((make_event("public", title="Private-test-material-must-not-be-persisted"),))
    query = ResearchQuery(
        job.request.question or "",
        job.period_from,
        job.period_to,
        focus=ResearchFocus.MEDIA,
        terms=("location hypothesis",),
    )

    class ForbiddenCollection:
        async def collect(self, *_: Any, **__: Any) -> ResearchBatch:
            pytest.fail("Private text must not be sent to public collection")

    store, receipt, effective = await collect_report_evidence_with_query(
        query,
        job.request,
        ForbiddenCollection(),  # type: ignore[arg-type]
        InMemoryEventStore,
        live,
        seed_events=job.seed_events,
    )
    assert effective == query
    assert receipt.collected_items == 0
    selected = select_for_job(
        store, {}, job, job.direction, runtime_query=effective, receipt=receipt
    )
    assert [item.event_id for item in selected.items] == [job.seed_events[0].id]


async def test_collection_boundary_rejects_an_unauthorised_effective_scope() -> None:
    request = ReportRequest(
        "ask",
        question="Zirconium",
        research_mode=ResearchMode.QUICK,
        research_terms=("zirconium",),
    )
    job = fixture_job(request)
    query = ResearchQuery("Zirconium", job.period_from, job.period_to, terms=("zirconium",))
    plan = ResearchPlan(
        query.question, query.since, query.until, query.languages, (), 6, 45.0, 200, replans=1
    )

    class UnsafeCollection:
        async def collect(self, *_: Any, **__: Any) -> ResearchBatch:
            return ResearchBatch(
                plan=plan,
                effective_query=replace(query, country_iso="US", terms=("different",)),
            )

    with pytest.raises(InvalidRequest, match="unauthorised search revision"):
        await collect_report_evidence_with_query(
            query,
            request,
            UnsafeCollection(),  # type: ignore[arg-type]
            InMemoryEventStore,
            InMemoryEventStore(),
        )
