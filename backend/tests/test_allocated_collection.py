"""Live collection spends only the exact tasks admitted by a current E01 allocation."""

from dataclasses import dataclass, field, replace

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence_with_query
from ase.application.research.budget import CollectionBudget
from ase.application.research.pacing import RequestPacer
from ase.application.research.service import ResearchCollectionService
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchMode, ResearchQuery
from ase.domain.research_tasks import PlannedQueryTask
from test_allocated_plan import REQUIREMENTS, Provider, _context, _query


@dataclass
class RecordingProvider(Provider):
    queries: list[ResearchQuery] = field(default_factory=list)

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        self.queries.append(query)
        return ResearchBatch()


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def immediate(_self: RequestPacer) -> None:
        pass

    monkeypatch.setattr(RequestPacer, "wait", immediate)


async def test_live_allocation_routes_exact_variants_and_receipts_with_initial_cap() -> None:
    providers = tuple(
        RecordingProvider(name, language="fr" if name == "alpha" else "en")
        for name in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf")
    )
    query = _query(
        tasks=(PlannedQueryTask("contrary", "alpha", "challenge", ("contrary drone policy",)),)
    )
    context = _context(providers)

    async def load(ids: tuple[str, ...]):
        assert ids == tuple(provider.id for provider in providers)
        return context

    result = await ResearchCollectionService(
        lambda _: providers, allocation_loader=load
    ).collect_with_requirements(query, REQUIREMENTS)

    assert result.plan is not None and result.plan.request_limit == 6
    assert sum(len(provider.queries) for provider in providers) == 6
    assert [row.terms for row in providers[0].queries] == [
        ("politique des drones",),
        ("contrary drone policy",),
    ]
    attempts = {row.task_id: row for row in result.attempts}
    assert attempts["operator:contrary"].purpose == "challenge"
    assert attempts["source:foxtrot"].status is CollectionStatus.BUDGET_EXHAUSTED
    assert attempts["source:golf"].explanation == "Source allocation: initial_operation_cap."
    assert len(providers[-1].queries) == 0


def test_active_preview_discloses_initial_cap_without_changing_legacy_preview() -> None:
    providers = (RecordingProvider("alpha"),)
    query = _query(mode=ResearchMode.DETAILED)

    async def load(_ids: tuple[str, ...]):
        return _context(providers)

    active = ResearchCollectionService(lambda _: providers, allocation_loader=load).plan(query)
    legacy = ResearchCollectionService(lambda _: providers).plan(query)
    assert active.request_limit == CollectionBudget.for_initial_mode(query.mode).requests
    assert legacy.request_limit == CollectionBudget.for_mode(query.mode).requests


async def test_unavailable_allocation_never_dispatches_or_leaks_operator_terms() -> None:
    providers = (RecordingProvider("alpha"),)
    private = "PRIVATE_SENTINEL operator terms"
    query = _query(tasks=(PlannedQueryTask("private", "alpha", "challenge", (private,)),))
    context = _context(providers, disabled=frozenset({"alpha"}))

    async def load(_ids: tuple[str, ...]):
        return context

    result = await ResearchCollectionService(
        lambda _: providers, allocation_loader=load
    ).collect_with_requirements(query, REQUIREMENTS)
    assert providers[0].queries == []
    assert {row.status for row in result.attempts} == {CollectionStatus.UNAVAILABLE}
    assert all(private not in row.explanation for row in result.attempts)


async def test_replan_preview_ignores_changed_terms_on_unadmitted_task() -> None:
    providers = tuple(RecordingProvider(name, language="fr") for name in "abcdefg")
    query = _query()
    # Six fixed variants are eligible. The only base-term search is outside the cap.
    query = replace(
        query,
        query_variants=(query.query_variants[0],),
        languages=("en", "fr"),
    )
    providers[-1].language = "en"
    context = _context(providers)

    async def load(_ids: tuple[str, ...]):
        return context

    async def revise(original: ResearchQuery, _first: ResearchBatch, _seconds: float):
        return replace(original, terms=("changed base terms",))

    result = await ResearchCollectionService(
        lambda _: providers, allocation_loader=load
    ).collect_with_requirements(query, REQUIREMENTS, replan=revise)

    assert result.effective_query == query
    assert result.plan is not None and result.plan.replans == 0
    assert providers[-1].queries == []
    assert sum(len(provider.queries) for provider in providers) == 6


async def test_report_hands_canonical_requirements_to_ranked_collection() -> None:
    query = replace(_query(), question="What changed?")
    request = ReportRequest(
        "ask",
        question=query.question,
        research_mode=ResearchMode.QUICK,
        canonical_requirements=REQUIREMENTS,
    )
    providers = (RecordingProvider("alpha"),)
    context = _context(providers)

    async def load(_ids: tuple[str, ...]):
        return context

    collection = ResearchCollectionService(lambda _: providers, allocation_loader=load)
    _, receipt, _ = await collect_report_evidence_with_query(
        query,
        request,
        collection,
        InMemoryEventStore,
        InMemoryEventStore(),
    )
    assert len(providers[0].queries) == 1
    assert receipt.attempts[0].status is CollectionStatus.EMPTY
