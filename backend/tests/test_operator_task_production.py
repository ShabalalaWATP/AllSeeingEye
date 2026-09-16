"""Real adapter capability and report production boundaries for operator tasks."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.research_records.company import SecSubmissionsProvider
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.production_collection import prepare_collection
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.production_types import Totals
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence
from ase.application.research.collection import ResearchCollector
from ase.application.research.pacing import PacedProvider, RequestPacer
from ase.application.research.service import ResearchCollectionService
from ase.application.research.source_admission import ControlledResearchProvider
from ase.container.research import private_research_store
from ase.domain.errors import InvalidRequest
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchMode
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS, MAX_COLLECTION_RECEIPTS
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from feeds_helpers import make_event
from production_integration_helpers import production_job
from research_records_helpers import CLOCK, COMPANY, RecordService, submissions
from test_operator_research_tasks import CANDIDATE, TASK, Provider, query


async def test_real_subject_lookup_never_repeats_subject_under_other_candidate_terms(monkeypatch):
    service = RecordService(monkeypatch, submissions())
    provider = SecSubmissionsProvider(service.http, CLOCK)
    task = replace(TASK, source_id=provider.id, terms=("another CIK candidate",))
    selected = replace(COMPANY, candidate_hypotheses=(CANDIDATE,), planned_tasks=(task,))
    try:
        batch = await ResearchCollector([provider]).collect(selected)
        assert len(service.requests) == 1
        assert "CIK0000001234" in str(service.requests[0].url)
        assert batch.attempts[1].status is CollectionStatus.UNSUPPORTED
        assert "does not support explicit task terms" in batch.attempts[1].explanation
        assert batch.plan.tasks[1].supported is False
        assert batch.plan.tasks[0].planned_terms_supported is False
    finally:
        await service.http.aclose()


@pytest.mark.parametrize("capability", [True, False, 1, "true", None])
def test_provider_wrappers_preserve_only_explicit_boolean_capability(capability):
    provider = Provider("source")
    provider.supports_planned_terms = capability
    wrapped = PacedProvider(ControlledResearchProvider(provider, None), RequestPacer())
    plan = ResearchCollectionService(lambda _: [wrapped]).plan(query())
    assert plan.tasks[0].planned_terms_supported is (capability is True)
    assert plan.tasks[1].supported is (capability is True)


async def test_report_production_passes_operator_scope_into_actual_collection(container, user):
    job = production_job(user, container.cipher)
    provider = Provider("source")
    request = replace(
        job.request,
        research_mode=ResearchMode.QUICK,
        research_terms=("baseline",),
        research_candidate_hypotheses=(CANDIDATE,),
        research_planned_tasks=(TASK,),
    )
    _, receipt, built = await prepare_collection(
        replace(job, request=request),
        None,
        Totals(),
        ResearchCollectionService(lambda _: [provider]),
        private_research_store,
        container.store,
        None,
    )
    assert [item.terms for item in provider.queries] == [("baseline",), TASK.terms]
    assert built.candidate_hypotheses == (CANDIDATE,)
    assert receipt.plan.candidate_hypotheses == (CANDIDATE,)
    assert receipt.attempts[1].candidate_id == "a"


async def test_operator_terms_influence_evidence_selection_without_promoting_identity(
    container, user
):
    job = production_job(user, container.cipher)
    request = replace(
        job.request,
        research_mode=ResearchMode.QUICK,
        research_candidate_hypotheses=(CANDIDATE,),
        research_planned_tasks=(TASK,),
    )
    # Identical date/source/grade, so only the explicit task phrase gives priority.
    when = job.now - timedelta(hours=1)
    plain = make_event("plain", title="Unrelated article", published_at=when)
    match = make_event("candidate", title="Exact operator terms reported", published_at=when)
    store = InMemoryEventStore()
    store.upsert((plain, match))
    result = select_for_job(store, {}, replace(job, request=request, terms=()), None)
    assert result.items[0].event_id == match.id
    assert result.items[0].reliability == plain.reliability.value


def test_optional_fields_remain_absent_when_legacy_receipts_are_reserialised():
    plan = ResearchCollectionService(lambda _: [Provider("source")]).plan(query())
    legacy_task = replace(plan.tasks[0], task_id=None, planned_terms_supported=False)
    legacy_plan = replace(plan, tasks=(legacy_task,), candidate_hypotheses=())
    receipt = ResearchReceipt.build(query(), (), 0, legacy_plan)
    saved = research_to_dict(receipt)
    assert "candidate_hypotheses" not in saved["plan"]
    assert "task_id" not in saved["plan"]["tasks"][0]
    assert "purpose" not in saved["plan"]["tasks"][0]
    assert research_to_dict(research_from_dict(saved)) == saved


async def test_expanded_plan_reserves_frozen_receipt_capacity_before_any_requests():

    providers = [
        Provider("source"),
        *(Provider(str(index)) for index in range(MAX_COLLECTION_PROVIDERS - 1)),
    ]
    service = ResearchCollectionService(lambda _: providers)
    retained = CollectionAttempt("retained", "Retained evidence", CollectionStatus.COMPLETED)
    selected = replace(query(), planned_tasks=tuple(replace(TASK, id=str(i)) for i in range(8)))
    with pytest.raises(InvalidRequest, match=f"{MAX_COLLECTION_RECEIPTS}-receipt"):
        await collect_report_evidence(
            selected,
            ReportRequest("ask"),
            service,
            private_research_store,
            InMemoryEventStore(),
            seed_attempts=(retained,),
        )
    assert all(not provider.queries for provider in providers)
