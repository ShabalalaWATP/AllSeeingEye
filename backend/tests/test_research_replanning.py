"""One private replan preserves scope, shared budgets, admission and exact pass history."""

import asyncio
from dataclasses import dataclass, field, replace
from datetime import timedelta

import pytest

from ase.application.research.budget import CollectionBudget
from ase.application.research.pacing import RequestPacer
from ase.application.research.service import ResearchCollectionService
from ase.domain.errors import RateLimited
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchMode
from ase.domain.research_plan import QueryVariant
from test_research_collection import QUERY, Provider, event


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch):
    async def wait(self):
        pass

    monkeypatch.setattr(RequestPacer, "wait", wait)


@dataclass
class Recording(Provider):
    queries: list = field(default_factory=list)
    found: bool = False

    async def collect(self, query):
        self.queries.append(query)
        if self.found or query.terms == ("revised",):
            return ResearchBatch(items=(event(self.id),))
        return await super().collect(query)


async def revised(query, batch, remaining):
    assert remaining > 0 and not batch.items
    return replace(query, terms=("revised",))


@pytest.mark.parametrize("change_later_language", [False, True])
async def test_fixed_variants_do_not_repeat_identical_searches_or_starve_remaining_sources(
    change_later_language,
) -> None:
    class LanguageProvider(Recording):
        language = "en"

    providers = [LanguageProvider(str(index)) for index in range(6)]
    fixed = QueryVariant("en", ("operator phrase",))
    query = replace(QUERY, languages=("en", "fa"), query_variants=(fixed,))
    if change_later_language:
        for provider in providers[3:]:
            provider.language = "fa"

    async def callback(original, first, remaining):
        return replace(
            original,
            terms=("changed base terms",),
            query_variants=(fixed, QueryVariant("fa", ("revised",))),
        )

    result = await ResearchCollectionService(lambda _: providers).collect(query, replan=callback)
    assert [len(provider.queries) for provider in providers] == [1] * 6
    assert [provider.queries[0].terms for provider in providers[:3]] == [("operator phrase",)] * 3
    assert [provider.queries[0].terms for provider in providers[3:]] == [
        ("revised",) if change_later_language else ("operator phrase",)
    ] * 3
    assert result.passes[1].plan.replans == int(change_later_language)
    if not change_later_language:
        assert result.passes[1].terms == QUERY.terms


async def test_replan_uses_same_inventory_and_shared_budget_with_bounded_exact_history() -> None:
    providers = [Recording(f"source-{index}") for index in range(64)]
    factory_calls = []

    def inventory(query):
        factory_calls.append(query)
        return providers

    result = await ResearchCollectionService(inventory).collect(QUERY, replan=revised)
    assert len(factory_calls) == 1
    assert sum(len(provider.queries) for provider in providers) == 6
    assert len(result.items) == 3 and len(result.attempts) == 64
    assert result.plan and result.plan.replans == 1
    assert len(result.passes) == 2
    assert result.passes[0].terms == QUERY.terms
    assert result.passes[1].terms == ("revised",)
    assert all(len(row.attempts) == 64 for row in result.passes)
    assert result.passes[0].attempts[0].status is CollectionStatus.EMPTY
    assert result.passes[1].attempts[0].status is CollectionStatus.COMPLETED
    assert result.attempts[0].status is CollectionStatus.COMPLETED


async def test_nonempty_initial_pass_completes_unattempted_explicit_selection_unchanged() -> None:
    providers = [Recording(str(index), found=True) for index in range(8)]
    query = replace(QUERY, source_ids=tuple(provider.id for provider in providers[1:]))

    async def forbidden(*args):
        pytest.fail("Nonempty evidence must not trigger another model call")

    result = await ResearchCollectionService(lambda _: providers).collect(query, replan=forbidden)
    assert providers[0].queries == []
    assert [len(provider.queries) for provider in providers[1:]] == [1, 1, 1, 1, 1, 1, 0]
    assert all(value == query for provider in providers for value in provider.queries)
    assert len(result.items) == 6
    assert result.plan and result.plan.replans == 0
    assert result.passes[1].plan and result.passes[1].plan.tasks == result.plan.tasks
    assert [row.source_id for row in result.passes[1].attempts] == ["4", "5", "6", "7"]


@pytest.mark.parametrize("outcome", ["none", "failure", "unchanged"])
async def test_declined_failed_or_unchanged_replan_uses_remaining_original_sources(outcome) -> None:
    providers = [Recording(str(index)) for index in range(8)]
    calls = 0

    async def callback(query, batch, remaining):
        nonlocal calls
        calls += 1
        if outcome == "failure":
            raise ValueError("private model output and credential")
        return query if outcome == "unchanged" else None

    result = await ResearchCollectionService(lambda _: providers).collect(QUERY, replan=callback)
    assert calls == 1
    assert [len(provider.queries) for provider in providers] == [1, 1, 1, 1, 1, 1, 0, 0]
    assert all(value == QUERY for provider in providers for value in provider.queries)
    assert "credential" not in repr(result)
    assert result.plan and result.plan.replans == 1


@pytest.mark.parametrize(
    "change",
    [
        {"question": "different question"},
        {"since": QUERY.since - timedelta(days=1)},
        {"until": QUERY.until + timedelta(days=1)},
        {"languages": ("fa",)},
        {"source_ids": ()},
        {"subject": "another entity"},
        {"country_iso": "GB"},
        {"focus": ResearchFocus.COMPANY},
        {"mode": ResearchMode.DETAILED},
    ],
)
async def test_callback_cannot_widen_any_scope_field(change) -> None:
    providers = [Recording(str(index)) for index in range(6)]

    async def unsafe(query, batch, remaining):
        return replace(query, terms=("revised",), **change)

    result = await ResearchCollectionService(lambda _: providers).collect(QUERY, replan=unsafe)
    assert len(result.items) == 0
    assert all(value == QUERY for provider in providers for value in provider.queries)
    assert sum(len(provider.queries) for provider in providers) == 6


async def test_failures_unsupported_and_empty_selection_never_trigger_replanning() -> None:
    async def forbidden(*args):
        pytest.fail("No successful empty search exists")

    for query, providers in (
        (QUERY, [Recording("failure", failure=True), Recording("unsupported", supported=False)]),
        (replace(QUERY, source_ids=()), [Recording("unselected")]),
    ):
        result = await ResearchCollectionService(lambda _, values=providers: values).collect(
            query, replan=forbidden
        )
        assert result.plan and result.plan.replans == 0


async def test_replan_timeout_cancels_callback_and_leaves_no_second_pass(monkeypatch) -> None:
    monkeypatch.setattr(CollectionBudget, "for_mode", lambda _: CollectionBudget(6, 0.02, 0.02, 10))
    cancelled = False

    async def callback(*args):
        nonlocal cancelled
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled = True
            raise

    providers = [Recording(str(index)) for index in range(6)]
    result = await ResearchCollectionService(lambda _: providers).collect(QUERY, replan=callback)
    assert cancelled and len(result.passes) == 1
    assert sum(len(provider.queries) for provider in providers) == 3


async def test_service_keeps_admission_through_replan_and_releases_on_cancellation() -> None:
    entered = 0
    ready = asyncio.Event()

    async def callback(*args):
        nonlocal entered
        entered += 1
        if entered == 2:
            ready.set()
        await asyncio.Event().wait()

    service = ResearchCollectionService(lambda _: [Recording("source")])
    tasks = [asyncio.create_task(service.collect(QUERY, replan=callback)) for _ in range(2)]
    await asyncio.wait_for(ready.wait(), 1)
    with pytest.raises(RateLimited):
        await service.collect(QUERY, replan=callback)
    with pytest.raises(RateLimited):
        await service.challenge_many((QUERY,))
    for task in tasks:
        task.cancel()
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    assert all(isinstance(outcome, asyncio.CancelledError) for outcome in outcomes)
    assert len((await service.collect(QUERY)).attempts) == 1


async def test_item_limit_stops_without_replan_or_reserved_requests() -> None:
    provider = Recording("full", ResearchBatch(items=tuple(event(str(i)) for i in range(200))))

    async def forbidden(*args):
        pytest.fail("A full item budget cannot replan")

    later = Recording("later")
    result = await ResearchCollectionService(lambda _: [provider, later]).collect(
        QUERY, replan=forbidden
    )
    assert len(result.items) == 200 and later.queries == []
    assert len(result.passes) == 1


async def test_cancellation_during_revised_fetch_stops_pass_and_releases_admission() -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    class WaitingRevision(Provider):
        async def collect(self, query):
            if query.terms != ("revised",):
                return ResearchBatch()
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

    service = ResearchCollectionService(lambda _: [WaitingRevision("source")])
    task = asyncio.create_task(service.collect(QUERY, replan=revised))
    await asyncio.wait_for(started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()
    assert len((await service.collect(QUERY)).attempts) == 1


async def test_second_pass_placeholders_do_not_erase_first_actual_attempts() -> None:
    providers = [Recording(str(index)) for index in range(6)]

    async def callback(query, batch, remaining):
        # Fill the item budget immediately on retry. Earlier searches for sources
        # 1 and 2 must survive their second-pass budget placeholders in the summary.
        providers[0].batch = ResearchBatch(items=tuple(event(str(i)) for i in range(200)))
        return replace(query, terms=("other",))

    result = await ResearchCollectionService(lambda _: providers).collect(QUERY, replan=callback)
    assert result.attempts[1].status is CollectionStatus.EMPTY
    assert result.passes[1].attempts[1].status is CollectionStatus.BUDGET_EXHAUSTED
    assert len(result.items) == 200
