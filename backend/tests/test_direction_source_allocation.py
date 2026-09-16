"""The direction call's requirements steer source allocation for a free-form ask."""

from dataclasses import replace

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence_with_query
from ase.application.research.service import ResearchCollectionService
from ase.application.research.source_allocation_types import AllocationProfile
from ase.application.research.source_allocator import allocate_sources
from ase.domain.direction import MAX_EEIS, MAX_SIRS, Direction
from ase.domain.direction_requirements import (
    MAX_DERIVED_REQUIREMENTS,
    direction_requirements,
    effective_requirements,
)
from ase.domain.research import ResearchMode
from ase.domain.research_brief_values import IntelligenceRequirement
from test_allocated_collection import RecordingProvider, no_pacing  # noqa: F401
from test_allocated_plan import _context, _query

DIRECTION = Direction(
    pir="How is the electricity grid being degraded?",
    sirs=("Which substation sites were struck?",),
    eeis=("Which repair crews have been deployed?",),
    search_terms=("grid", "substation"),
)


def test_direction_becomes_prioritised_intelligence_requirements():
    rows = direction_requirements(DIRECTION)
    assert [row.id for row in rows] == ["PIR-1", "SIR-1", "EEI-1"]
    assert [row.required for row in rows] == [True, True, False]
    assert [row.priority for row in rows] == [1, 2, 3]
    assert rows[0].question == DIRECTION.pir
    assert direction_requirements(None) == ()


def test_derived_requirements_stay_inside_the_brief_contract_bounds():
    crowded = Direction(
        pir="Main question",
        sirs=tuple(f"Supporting question {index}" for index in range(1, MAX_SIRS + 1)),
        eeis=tuple(f"Essential element {index}" for index in range(1, MAX_EEIS + 1)),
    )
    rows = direction_requirements(crowded)
    assert len(rows) == MAX_DERIVED_REQUIREMENTS
    assert len({row.id for row in rows}) == MAX_DERIVED_REQUIREMENTS
    assert all(1 <= row.priority <= 12 for row in rows)


def test_a_pinned_brief_takes_precedence_over_the_direction_call():
    pinned = (IntelligenceRequirement("brief-1", "Pinned question"),)
    assert effective_requirements(pinned, DIRECTION) == pinned
    assert effective_requirements((), DIRECTION) == direction_requirements(DIRECTION)


def _profiles(providers, terms):
    return {
        provider.id: AllocationProfile(terms.get(provider.id, ()), "reviewed for the test")
        for provider in providers
    }


def test_a_source_is_planned_for_the_requirement_it_can_answer():
    """The question shares no words with the source; a stated requirement does."""
    providers = tuple(RecordingProvider(name) for name in ("alpha", "bravo"))
    context = _context(providers)
    query = replace(_query(), question="What changed?", subject=None, terms=())
    options = {
        "authorised_ids": context.authorised_ids,
        "provider_support": dict.fromkeys((row.capability.id for row in context.resolved), True),
        "reviewed_profiles": _profiles(providers, {providers[0].id: ("substation",)}),
    }
    without = allocate_sources(query, (), context.resolved, **options)
    with_requirements = allocate_sources(
        query, direction_requirements(DIRECTION), context.resolved, **options
    )
    assert providers[0].id not in without.provider_ids
    assert providers[0].id in with_requirements.provider_ids
    covered = dict(with_requirements.requirement_sources)
    assert providers[0].id in covered["SIR-1"]
    receipt = next(row for row in with_requirements.receipts if row.source_id == providers[0].id)
    assert "SIR-1" in receipt.requirement_ids
    assert any(name == "requirements" and value > 0 for name, value in receipt.score_components)


def test_allocation_stays_pure_and_order_independent_with_derived_requirements():
    providers = tuple(RecordingProvider(name) for name in ("alpha", "bravo"))
    context = _context(providers)
    query = replace(_query(), question="What changed?", subject=None, terms=())
    options = {
        "authorised_ids": context.authorised_ids,
        "provider_support": dict.fromkeys((row.capability.id for row in context.resolved), True),
        "reviewed_profiles": _profiles(providers, {providers[0].id: ("substation",)}),
    }
    rows = direction_requirements(DIRECTION)
    first = allocate_sources(query, rows, context.resolved, **options)
    again = allocate_sources(
        query, tuple(reversed(rows)), tuple(reversed(context.resolved)), **options
    )
    assert first == again
    assert first.retrieved_at is None and first.attempted_operations == 0


async def test_report_collection_derives_requirements_when_no_brief_is_pinned() -> None:
    query = replace(_query(), question="What changed?")
    request = ReportRequest("ask", question=query.question, research_mode=ResearchMode.QUICK)
    providers = (RecordingProvider("alpha"),)
    context = _context(providers)
    seen: list[tuple[IntelligenceRequirement, ...]] = []

    async def load(_ids: tuple[str, ...]):
        return context

    collection = ResearchCollectionService(lambda _: providers, allocation_loader=load)
    original = collection.collect_with_requirements

    async def record(candidate, requirements, **kwargs):
        seen.append(requirements)
        return await original(candidate, requirements, **kwargs)

    collection.collect_with_requirements = record  # type: ignore[method-assign]
    await collect_report_evidence_with_query(
        query,
        request,
        collection,
        InMemoryEventStore,
        InMemoryEventStore(),
        direction=DIRECTION,
    )
    assert seen == [direction_requirements(DIRECTION)]


async def test_no_direction_and_no_brief_supplies_no_requirements() -> None:
    query = replace(_query(), question="What changed?")
    request = ReportRequest("ask", question=query.question, research_mode=ResearchMode.QUICK)
    providers = (RecordingProvider("alpha"),)
    context = _context(providers)

    async def load(_ids: tuple[str, ...]):
        return context

    collection = ResearchCollectionService(lambda _: providers, allocation_loader=load)
    seen: list[tuple[IntelligenceRequirement, ...]] = []
    original = collection.collect_with_requirements

    async def record(candidate, requirements, **kwargs):
        seen.append(requirements)
        return await original(candidate, requirements, **kwargs)

    collection.collect_with_requirements = record  # type: ignore[method-assign]
    await collect_report_evidence_with_query(
        query, request, collection, InMemoryEventStore, InMemoryEventStore()
    )
    assert seen == [()]
