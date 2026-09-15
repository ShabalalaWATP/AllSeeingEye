"""Call outcomes, concurrent settlement, reconciliation and observation mode."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest

from ai_usage_helpers import NOW, accounting, add_policy, policy, reservations, summaries
from ase.adapters.persistence.ai_usage import SqlAiUsageRepository
from ase.adapters.persistence.base import Base
from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.application.ai_usage import AiUsageAccounting
from ase.application.ai_usage_gateway import AllowanceLlmGateway
from ase.application.ports.llm import LlmGatewayError, LlmGatewayTimeout
from ase.domain.ai_usage import (
    STALE_RESERVATION_AGE,
    AiAttribution,
    AiCallOutcome,
    AiReservationStatus,
)
from ase.domain.llm import LlmResult
from report_job_budget_helpers import REQUEST


class Provider:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    async def complete(self, *_args):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


def gateway(container, provider, user_id, team_id=None) -> AllowanceLlmGateway:
    return AllowanceLlmGateway(
        provider,
        accounting(container),
        attribution=AiAttribution.actor(user_id, team_id),
        profile_id=None,
    )


async def call(wrapped):
    return await wrapped.complete("https://model.example", "secret", "luna", REQUEST)


async def test_completed_call_settles_reported_usage(container, user):
    await add_policy(container, policy(limit=5, tokens=100_000))
    result = await call(gateway(container, Provider(LlmResult("{}", "luna", 1, 12, 34)), user.id))
    assert result.completion_tokens == 34
    [row] = await reservations(container)
    assert (row.status, row.actual_tokens, row.ok) == (AiReservationStatus.SETTLED, 46, True)
    [summary] = await summaries(container, user.id)
    assert (summary.used_requests, summary.used_tokens, summary.reserved_tokens) == (1, 46, 0)


async def test_provider_error_counts_request_with_zero_tokens(container, user):
    await add_policy(container, policy(limit=5, tokens=100_000))
    with pytest.raises(LlmGatewayError):
        await call(gateway(container, Provider(error=LlmGatewayError("refused")), user.id))
    [row] = await reservations(container)
    assert (row.status, row.actual_tokens, row.error) == (
        AiReservationStatus.SETTLED,
        0,
        "provider_error",
    )
    [summary] = await summaries(container, user.id)
    assert (summary.used_requests, summary.used_tokens, summary.reserved_tokens) == (1, 0, 0)


async def test_timeout_after_dispatch_stays_held_as_unknown(container, user):
    await add_policy(container, policy(limit=5, tokens=100_000))
    with pytest.raises(LlmGatewayTimeout):
        await call(gateway(container, Provider(error=LlmGatewayTimeout("slow")), user.id))
    [row] = await reservations(container)
    assert row.status is AiReservationStatus.UNKNOWN and row.dispatched_at is not None
    [summary] = await summaries(container, user.id)
    # Not released and not settled: the reservation is still held conservatively.
    assert (summary.used_requests, summary.reserved_requests) == (0, 1)
    assert summary.reserved_tokens == row.reserved_tokens


async def test_cancellation_while_waiting_before_dispatch_releases_reservation(container, user):
    await add_policy(container, policy(limit=5, tokens=100_000))
    ledger = accounting(container)
    provider = Provider(LlmResult("{}", "luna", 1, 1, 1))
    wrapped = AllowanceLlmGateway(
        provider, ledger, attribution=AiAttribution.actor(user.id), profile_id=None
    )
    waiting = asyncio.Event()
    original = ledger.mark_dispatched

    async def slow_dispatch(batch):
        waiting.set()
        await asyncio.sleep(10)
        await original(batch)

    ledger.mark_dispatched = slow_dispatch  # type: ignore[method-assign]
    task = asyncio.create_task(call(wrapped))
    await waiting.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert provider.calls == 0
    [row] = await reservations(container)
    assert row.status is AiReservationStatus.RELEASED and row.dispatched_at is None
    [summary] = await summaries(container, user.id)
    assert (summary.used_requests, summary.reserved_requests, summary.reserved_tokens) == (0, 0, 0)


async def test_observation_mode_records_usage_without_a_policy(container, user):
    result = await call(gateway(container, Provider(LlmResult("{}", "luna", 1, 5, 7)), user.id))
    assert result.prompt_tokens == 5
    assert await reservations(container) == []
    async with container.session_factory() as session:
        totals = await container.repositories(session).ai_usage.account_totals(
            user.id, container.clock.now()
        )
    assert (totals.used_requests, totals.used_tokens, totals.unknown_requests) == (1, 12, 0)


async def test_reconciliation_releases_undispatched_and_holds_dispatched(container, user, clock):
    await add_policy(container, policy(limit=5, tokens=100_000))
    ledger = accounting(container)
    orphan = await ledger.reserve(
        AiAttribution.actor(user.id), profile_id=None, model="m", purpose="t", requested_tokens=9
    )
    sent = await ledger.reserve(
        AiAttribution.actor(user.id), profile_id=None, model="m", purpose="t", requested_tokens=7
    )
    await ledger.mark_dispatched(sent)
    assert (await ledger.reconcile()).released == 0  # Too recent to judge.
    clock.advance(STALE_RESERVATION_AGE + timedelta(minutes=1))
    outcome = await ledger.reconcile()
    assert (outcome.released, outcome.unknown) == (1, 1)
    statuses = {row.call_id: row.status for row in await reservations(container)}
    assert statuses[orphan.call_id] is AiReservationStatus.RELEASED
    assert statuses[sent.call_id] is AiReservationStatus.UNKNOWN
    [summary] = await summaries(container, user.id)
    assert (summary.reserved_requests, summary.reserved_tokens) == (1, 7)
    async with container.session_factory() as session:
        repo = container.repositories(session).ai_usage
        assert await repo.count_reservations(AiReservationStatus.UNKNOWN) == 1
        totals = await repo.account_totals(user.id, clock.now())
    assert totals.unknown_requests == 1
    assert (await ledger.reconcile()) == type(outcome)(0, 0)


async def test_reserve_runs_bounded_reconciliation_opportunistically(container, user, clock):
    await add_policy(container, policy(limit=1, tokens=100))
    ticks = iter([0.0, 1000.0])
    ledger = AiUsageAccounting(
        container.session_factory,
        lambda session: container.repositories(session).ai_usage,
        container.clock,
        monotonic=lambda: next(ticks),
    )
    attribution = AiAttribution.actor(user.id)
    await ledger.reserve(attribution, profile_id=None, model="m", purpose="t", requested_tokens=5)
    clock.advance(STALE_RESERVATION_AGE * 2)
    # The orphan is released during admission, freeing the single request allowance.
    batch = await ledger.reserve(
        attribution, profile_id=None, model="m", purpose="t", requested_tokens=5
    )
    assert len(batch.reservations) == 1


async def test_concurrent_reserve_and_settle_never_lose_increments(tmp_path):
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'settle-race.db'}")
    factory = create_session_factory(engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    current = policy(limit=None, tokens=None)
    async with factory() as session:
        await SqlAiUsageRepository(session).add_policy(current)
        await session.commit()

    class Clock:
        def now(self):
            return NOW

    ledger = AiUsageAccounting(factory, SqlAiUsageRepository, Clock())
    attribution = AiAttribution.system_work()
    rounds = 12

    async def cycle() -> None:
        batch = await ledger.reserve(
            attribution, profile_id=None, model="m", purpose="race", requested_tokens=10
        )
        await ledger.mark_dispatched(batch)
        await ledger.finish(batch, AiCallOutcome.COMPLETED, prompt_tokens=1, completion_tokens=2)

    async def holder() -> None:
        await ledger.reserve(
            attribution, profile_id=None, model="m", purpose="hold", requested_tokens=4
        )

    await asyncio.gather(*(cycle() for _ in range(rounds)), *(holder() for _ in range(rounds)))
    async with factory() as session:
        repo = SqlAiUsageRepository(session)
        [summary] = await repo.summaries_for([current], NOW)
        totals = await repo.system_totals(NOW)
    assert (summary.used_requests, summary.used_tokens) == (rounds, rounds * 3)
    assert (summary.reserved_requests, summary.reserved_tokens) == (rounds, rounds * 4)
    assert (totals.used_requests, totals.used_tokens) == (rounds, rounds * 3)
    await engine.dispose()


async def test_unknown_system_attribution_is_rejected():
    with pytest.raises(ValueError, match="System AI work"):
        AiAttribution(uuid4(), None, True)
    with pytest.raises(ValueError, match="initiating account"):
        AiAttribution(None)
