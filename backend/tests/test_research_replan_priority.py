"""A revised search reaches untried admitted sources before repeating earlier work."""

from dataclasses import dataclass, field, replace
from datetime import timedelta

import pytest

from ase.application.research.pacing import RequestPacer
from ase.application.research.service import ResearchCollectionService
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery
from test_allocated_plan import REQUIREMENTS, Provider, _context, _query
from test_research_collection import event


@dataclass
class Source(Provider):
    queries: list[ResearchQuery] = field(default_factory=list)

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        self.queries.append(query)
        if self.id == "alpha":
            raise ValueError("Synthetic retrieval failure")
        if self.id in {"bravo", "charlie"}:
            return ResearchBatch()
        return ResearchBatch(items=(event(self.id, query.until - timedelta(hours=1)),))


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def immediate(_self: RequestPacer) -> None:
        pass

    monkeypatch.setattr(RequestPacer, "wait", immediate)


@pytest.mark.parametrize("allocated", [False, True])
async def test_changed_terms_try_unattempted_sources_within_the_existing_six_operations(
    allocated: bool,
) -> None:
    providers = tuple(
        Source(name) for name in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf")
    )
    context = _context(providers)

    async def load(_ids: tuple[str, ...]):
        return context

    async def revise(query: ResearchQuery, first: ResearchBatch, _seconds: float):
        assert not first.items
        return replace(query, terms=("revised drone policy",))

    service = ResearchCollectionService(
        lambda _: providers, allocation_loader=load if allocated else None
    )
    result = await service.collect_with_requirements(_query(), REQUIREMENTS, replan=revise)

    assert [len(provider.queries) for provider in providers] == [1, 1, 1, 1, 1, 1, 0]
    assert {item.id for item in result.items} == {"delta", "echo", "foxtrot"}
    assert [provider.queries[0].terms for provider in providers[3:6]] == [
        ("revised drone policy",)
    ] * 3
    assert result.plan is not None and result.plan.replans == 1
    assert result.plan.request_limit == 6
    by_source = {attempt.source_id: attempt for attempt in result.attempts}
    assert by_source["alpha"].status is CollectionStatus.FAILED
    assert by_source["bravo"].status is CollectionStatus.EMPTY
    assert by_source["golf"].status is CollectionStatus.BUDGET_EXHAUSTED
    if allocated:
        assert by_source["golf"].explanation == "Source allocation: initial_operation_cap."


async def test_second_pass_priority_does_not_promote_newly_disabled_sources() -> None:
    providers = tuple(
        Source(name) for name in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf")
    )
    disabled: frozenset[str] = frozenset()

    async def load(_ids: tuple[str, ...]):
        return _context(providers, disabled=disabled)

    async def revise(query: ResearchQuery, _first: ResearchBatch, _seconds: float):
        nonlocal disabled
        disabled = frozenset({"delta"})
        return replace(query, terms=("revised drone policy",))

    result = await ResearchCollectionService(
        lambda _: providers, allocation_loader=load
    ).collect_with_requirements(_query(), REQUIREMENTS, replan=revise)

    assert [len(provider.queries) for provider in providers] == [1, 1, 1, 0, 1, 1, 1]
    assert {item.id for item in result.items} == {"echo", "foxtrot", "golf"}
    assert (
        next(row for row in result.attempts if row.source_id == "delta").status
        is CollectionStatus.UNAVAILABLE
    )
