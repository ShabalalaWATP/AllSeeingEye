"""Initial and revised collection passes cannot replenish a run's admitted resources."""

import asyncio
from dataclasses import dataclass, replace

import pytest

from ase.application.research.collection import (
    CollectionBudget,
    CollectionRunBudget,
    ResearchCollector,
)
from ase.domain.errors import InvalidRequest
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchMode
from test_research_collection import QUERY, Provider, event


@dataclass
class Clock:
    now: float = 0

    def __call__(self) -> float:
        return self.now


@pytest.mark.parametrize("mode", [ResearchMode.QUICK, ResearchMode.DETAILED])
async def test_two_passes_share_mode_request_ceiling_and_reserve_capacity(mode) -> None:
    limits = CollectionBudget.for_mode(mode)
    state = CollectionRunBudget(limits)
    initial = [Provider(f"first-{index}") for index in range(limits.requests)]
    revised = [Provider(f"revised-{index}") for index in range(limits.requests)]
    query = replace(QUERY, mode=mode)
    first = await ResearchCollector(initial).collect(
        query, run_budget=state, request_allowance=limits.requests - 2
    )
    assert state.remaining_requests == 2
    assert [row.status for row in first.attempts[-2:]] == [CollectionStatus.BUDGET_EXHAUSTED] * 2
    second = await ResearchCollector(revised).collect(query, run_budget=state)
    assert sum(provider.called for provider in (*initial, *revised)) == limits.requests
    assert state.requests_used == limits.requests
    assert state.remaining_requests == 0
    assert [row.status for row in second.attempts[:2]] == [CollectionStatus.EMPTY] * 2
    assert all(row.status is CollectionStatus.BUDGET_EXHAUSTED for row in second.attempts[2:])
    assert first.plan and second.plan
    assert first.plan.request_limit == second.plan.request_limit == limits.requests


async def test_unique_items_are_charged_once_across_passes_and_originals_are_not_replaced() -> None:
    state = CollectionRunBudget(CollectionBudget(6, 45, 12, 3))
    original = event("shared")
    first = await ResearchCollector(
        [Provider("first", ResearchBatch(items=(original, original, event("a"))))]
    ).collect(QUERY, run_budget=state)
    second_provider = Provider(
        "second",
        ResearchBatch(items=(original.with_changes(title="changed"), event("b"), event("c"))),
    )
    skipped = Provider("skipped")
    second = await ResearchCollector([second_provider, skipped]).collect(QUERY, run_budget=state)
    assert first.items == (original, event("a"))
    assert second.items == (event("b"),)
    assert second.attempts[0].result_count == 1
    assert skipped.called == 0
    assert state.retained_count == 3 and state.remaining_items == 0
    assert state.requests_used == 2


async def test_time_between_passes_consumes_original_deadline() -> None:
    clock = Clock()
    state = CollectionRunBudget(CollectionBudget(6, 1, 1, 10), clock=clock)
    first, revised = Provider("first"), Provider("revised")
    await ResearchCollector([first]).collect(QUERY, run_budget=state, request_allowance=1)
    clock.now = 1.1
    result = await ResearchCollector([revised]).collect(QUERY, run_budget=state)
    assert state.remaining_seconds == 0
    assert revised.called == 0 and state.requests_used == 1
    assert result.attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED


async def test_revised_request_timeout_uses_only_remaining_run_time(monkeypatch) -> None:
    clock = Clock()
    state = CollectionRunBudget(CollectionBudget(6, 1, 1, 10), clock=clock)
    observed: list[float] = []
    original = ResearchCollector._fetch

    async def fetch(provider, query, seconds):
        observed.append(seconds)
        return await original(provider, query, seconds)

    monkeypatch.setattr(ResearchCollector, "_fetch", staticmethod(fetch))
    await ResearchCollector([Provider("first")]).collect(QUERY, run_budget=state)
    clock.now = 0.75
    await ResearchCollector([Provider("revised")]).collect(QUERY, run_budget=state)
    assert observed == [1, 0.25]


async def test_failed_and_timed_out_requests_are_not_refunded_between_passes() -> None:
    state = CollectionRunBudget(CollectionBudget(2, 1, 0.01, 10))
    failed, timed, revised = (
        Provider("failed", failure=True),
        Provider("timed", wait=True),
        Provider("new"),
    )
    first = await ResearchCollector([failed, timed]).collect(QUERY, run_budget=state)
    second = await ResearchCollector([revised]).collect(QUERY, run_budget=state)
    assert [row.status for row in first.attempts] == [
        CollectionStatus.FAILED,
        CollectionStatus.TIMED_OUT,
    ]
    assert revised.called == 0 and state.requests_used == 2
    assert second.attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED


async def test_cancellation_consumes_request_but_releases_serial_pass_guard() -> None:
    state = CollectionRunBudget(CollectionBudget(2, 45, 12, 10))
    waiting = Provider("waiting", wait=True)
    collector = ResearchCollector([waiting])
    task = asyncio.create_task(collector.collect(QUERY, run_budget=state))
    await asyncio.sleep(0)
    with pytest.raises(ValueError, match="serial"):
        await ResearchCollector([Provider("overlap")]).collect(QUERY, run_budget=state)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert waiting.cancelled and state.requests_used == 1
    revised = Provider("revised", ResearchBatch(items=(event("new"),)))
    result = await ResearchCollector([revised]).collect(QUERY, run_budget=state)
    assert result.items == (event("new"),)
    assert state.requests_used == 2


async def test_zero_allowance_and_unsupported_sources_do_not_charge_run_budget() -> None:
    state = CollectionRunBudget(CollectionBudget(2, 45, 12, 10))
    unsupported, supported = Provider("unsupported", supported=False), Provider("supported")
    result = await ResearchCollector([unsupported, supported]).collect(
        QUERY, run_budget=state, request_allowance=0
    )
    assert [row.status for row in result.attempts] == [
        CollectionStatus.UNSUPPORTED,
        CollectionStatus.BUDGET_EXHAUSTED,
    ]
    assert state.requests_used == 0 and supported.called == unsupported.called == 0


@pytest.mark.parametrize("allowance", [-1, 33, True, 1.5])
async def test_invalid_pass_allowance_rejected_before_outbound_work(allowance) -> None:
    provider = Provider("never")
    with pytest.raises(ValueError, match="allowance"):
        await ResearchCollector([provider]).collect(QUERY, request_allowance=allowance)
    assert provider.called == 0


async def test_shared_limits_cannot_be_overridden_and_invalid_plan_does_not_consume_them() -> None:
    limits = CollectionBudget(2, 45, 12, 10)
    state = CollectionRunBudget(limits)
    provider = Provider("source")
    collector = ResearchCollector([provider])
    with pytest.raises(ValueError, match="either"):
        await collector.collect(QUERY, budget=limits, run_budget=state)
    with pytest.raises(InvalidRequest):
        await collector.collect(replace(QUERY, source_ids=("unknown",)), run_budget=state)
    assert state.requests_used == 0 and provider.called == 0
    await collector.collect(QUERY, run_budget=state)
    assert state.requests_used == 1
