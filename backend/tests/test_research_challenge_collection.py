"""Counterevidence requests share budgets and give later judgements a turn."""

import asyncio
from dataclasses import replace

import pytest
from tests.test_research_collection import QUERY, Provider, event

from ase.application.research.challenge_collection import collect_challenges
from ase.application.research.pacing import PacedProvider, RequestPacer
from ase.application.research.service import ResearchCollectionService
from ase.domain.errors import RateLimited
from ase.domain.research import CollectionStatus, ResearchBatch


async def test_challenge_budget_is_shared_and_round_robin() -> None:
    called: list[tuple[str, str]] = []

    class Recording(Provider):
        async def collect(self, query):  # type: ignore[no-untyped-def]
            called.append((query.question, self.id))
            return ResearchBatch(items=(event(f"{query.question}-{self.id}"),))

    queries = tuple(replace(QUERY, question=f"KJ{index}") for index in range(8))
    results = await collect_challenges(queries, lambda query: [Recording("one"), Recording("two")])
    assert called == [(f"KJ{index}", "one") for index in range(6)]
    assert len(results) == 8
    assert results[6].attempts[0].status == CollectionStatus.BUDGET_EXHAUSTED
    assert "does not confirm" in results[6].attempts[0].explanation
    assert sum(len(batch.items) for batch in results) == 6


async def test_unsupported_queries_do_not_consume_requests_and_items_are_bounded() -> None:
    unsupported = Provider("unsupported", supported=False)
    full = Provider("full", ResearchBatch(items=tuple(event(str(i)) for i in range(300))))
    results = await collect_challenges((QUERY, QUERY), lambda query: [unsupported, full])
    assert unsupported.called == 0 and full.called == 2
    assert len({item.id for batch in results for item in batch.items}) <= 200
    assert all(batch.attempts[0].status == CollectionStatus.UNSUPPORTED for batch in results)
    assert await collect_challenges((), lambda query: []) == ()
    with pytest.raises(ValueError):
        await collect_challenges((QUERY,) * 33, lambda query: [])


async def test_shared_admission_rejects_third_run_and_releases_on_cancel() -> None:
    provider = Provider("waiting", wait=True)
    service = ResearchCollectionService(lambda query: [provider])
    tasks = [
        asyncio.create_task(service.collect(QUERY)),
        asyncio.create_task(service.challenge_many((QUERY,))),
    ]
    await asyncio.sleep(0)
    with pytest.raises(RateLimited):
        await service.collect(QUERY)
    with pytest.raises(RateLimited):
        await service.challenge_many((QUERY,))
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    provider.wait = False
    assert len((await service.collect(QUERY)).attempts) == 1


async def test_request_pacing_is_shared_between_provider_instances() -> None:
    starts: list[float] = []

    class Recording(Provider):
        async def collect(self, query):  # type: ignore[no-untyped-def]
            starts.append(asyncio.get_running_loop().time())
            return ResearchBatch()

    pacer = RequestPacer()
    first, second = PacedProvider(Recording("one"), pacer), PacedProvider(Recording("two"), pacer)
    await asyncio.gather(first.collect(QUERY), second.collect(QUERY))
    assert starts[1] - starts[0] >= 0.12
