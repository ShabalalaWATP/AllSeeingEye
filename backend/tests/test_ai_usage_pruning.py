"""Bounded pruning of expired AI reservations, counters and totals."""

from __future__ import annotations

import logging
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from ai_usage_helpers import accounting, add_policy, policy
from ase.adapters.persistence.ai_usage_models import (
    NIL_KEY,
    AiUsageCounterRow,
    AiUsageReservationRow,
    AiUsageTotalRow,
)
from ase.application.ai_usage import (
    PRUNE_BATCH,
    PRUNE_INTERVAL_SECONDS,
    RECONCILE_INTERVAL_SECONDS,
    AiUsageAccounting,
    AiUsagePruned,
)
from ase.domain.ai_usage import (
    PERIOD_RETENTION,
    RESERVATION_RETENTION,
    AiAttribution,
    AiCallOutcome,
)
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

MODEL = "fixture-model"


async def _reservation(container, policy_id: UUID, status: str, age: timedelta) -> UUID:
    end = container.clock.now() - age
    row_id = uuid4()
    async with container.session_factory() as session:
        session.add(
            AiUsageReservationRow(
                id=row_id,
                call_id=uuid4(),
                policy_id=policy_id,
                user_id=None,
                team_id=None,
                system=True,
                profile_id=None,
                model=MODEL,
                purpose="prune-test",
                period_start=end - timedelta(days=1),
                period_end=end,
                reserved_tokens=5,
                status=status,
                created_at=end - timedelta(days=1),
            )
        )
        await session.commit()
    return row_id


async def _counter(container, policy_id: UUID, age: timedelta, reserved: int = 0) -> None:
    end = container.clock.now() - age
    async with container.session_factory() as session:
        session.add(
            AiUsageCounterRow(
                policy_id=policy_id,
                period_start=end - timedelta(days=1),
                period_end=end,
                used_requests=3,
                reserved_requests=reserved,
                used_tokens=30,
                reserved_tokens=reserved * 5,
            )
        )
        await session.commit()


async def _total(container, age: timedelta, user_key: UUID = NIL_KEY) -> None:
    end = container.clock.now() - age
    async with container.session_factory() as session:
        session.add(
            AiUsageTotalRow(
                period_start=end - timedelta(days=30),
                team_key=NIL_KEY,
                user_key=user_key,
                period_end=end,
                used_requests=4,
                used_tokens=40,
            )
        )
        await session.commit()


async def _ids(container, row) -> set:
    async with container.session_factory() as session:
        if row is AiUsageReservationRow:
            return set(await session.scalars(select(row.id)))
        return set((await session.execute(select(row.period_end))).scalars())


async def _count(container, row) -> int:
    async with container.session_factory() as session:
        return int(await session.scalar(select(func.count()).select_from(row)) or 0)


async def test_prune_removes_only_expired_finished_rows(container):
    current = policy()
    await add_policy(container, current)
    expired = RESERVATION_RETENTION + timedelta(days=1)
    recent = RESERVATION_RETENTION - timedelta(days=1)
    settled = await _reservation(container, current.id, "settled", expired)
    released = await _reservation(container, current.id, "released", expired)
    kept = {
        await _reservation(container, current.id, "reserved", expired),
        await _reservation(container, current.id, "unknown", expired),
        await _reservation(container, current.id, "settled", recent),
    }
    old_period = PERIOD_RETENTION + timedelta(days=1)
    await _counter(container, current.id, old_period)
    await _counter(container, current.id, old_period + timedelta(days=5), reserved=1)
    await _counter(container, current.id, PERIOD_RETENTION - timedelta(days=1))
    await _total(container, old_period)
    await _total(container, PERIOD_RETENTION - timedelta(days=1))

    pruned = await accounting(container).prune()

    assert pruned == AiUsagePruned(reservations=2, counters=1, totals=1)
    remaining = await _ids(container, AiUsageReservationRow)
    assert remaining == kept and not {settled, released} & remaining
    now = container.clock.now()
    counter_ends = await _ids(container, AiUsageCounterRow)
    # The ended counter still carrying a held reservation survives with the recent one.
    assert counter_ends == {
        now - old_period - timedelta(days=5),
        now - PERIOD_RETENTION + timedelta(days=1),
    }
    assert await _ids(container, AiUsageTotalRow) == {now - PERIOD_RETENTION + timedelta(days=1)}
    assert await accounting(container).prune() == AiUsagePruned()


async def test_prune_respects_the_batch_bound(container):
    current = policy()
    await add_policy(container, current)
    for _ in range(7):
        await _reservation(container, current.id, "settled", RESERVATION_RETENTION * 2)
    for day in range(4):
        await _total(container, PERIOD_RETENTION + timedelta(days=day + 1), user_key=uuid4())
    ledger = accounting(container)
    first = await ledger.prune(limit=3)
    assert first == AiUsagePruned(reservations=3, counters=0, totals=3) and first.reached(3)
    assert await _count(container, AiUsageReservationRow) == 4
    assert await _count(container, AiUsageTotalRow) == 1
    assert await ledger.prune(limit=3) == AiUsagePruned(3, 0, 1)
    last = await ledger.prune(limit=3)
    assert last == AiUsagePruned(1, 0, 0) and not last.reached(3)


async def test_pruning_leaves_current_summaries_and_self_usage_unchanged(
    client, container, user, caplog
):
    current = policy(limit=10, tokens=10_000)
    await add_policy(container, current)
    ledger = accounting(container)
    for _ in range(2):
        batch = await ledger.reserve(
            AiAttribution.actor(user.id),
            profile_id=None,
            model=MODEL,
            purpose="prune-test",
            requested_tokens=50,
        )
        await ledger.mark_dispatched(batch)
        await ledger.finish(batch, AiCallOutcome.COMPLETED, prompt_tokens=4, completion_tokens=6)
    await _reservation(container, current.id, "settled", RESERVATION_RETENTION * 2)
    await _total(container, PERIOD_RETENTION * 2, user_key=user.id)
    await _counter(container, current.id, PERIOD_RETENTION * 2)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    before = (await client.get("/api/ai-usage/me", headers=bearer(token))).json()
    assert before["items"][0]["used_requests"] == 2
    assert before["observed"]["used_tokens"] == 20

    with caplog.at_level(logging.INFO, logger="ase.application.ai_usage"):
        pruned = await ledger.prune()

    assert pruned == AiUsagePruned(reservations=1, counters=1, totals=1)
    after = (await client.get("/api/ai-usage/me", headers=bearer(token))).json()
    assert after == before
    [record] = [item for item in caplog.records if item.msg == "ai_usage.pruned"]
    assert (record.reservations, record.counters, record.totals) == (1, 1, 1)
    assert str(user.id) not in record.getMessage() and str(user.id) not in str(record.__dict__)


class _Recording(AiUsageAccounting):
    def __init__(self, container, ticks, results) -> None:
        super().__init__(
            container.session_factory,
            lambda session: container.repositories(session).ai_usage,
            container.clock,
            monotonic=lambda: next(ticks),
        )
        self.results = iter(results)
        self.prunes = 0

    async def prune(self, limit: int = PRUNE_BATCH) -> AiUsagePruned:
        self.prunes += 1
        result = next(self.results)
        if isinstance(result, BaseException):
            raise result
        return result


async def _admit(ledger: AiUsageAccounting) -> None:
    await ledger.reserve(
        AiAttribution.system_work(),
        profile_id=None,
        model=MODEL,
        purpose="prune-test",
        requested_tokens=1,
    )


async def test_admission_prunes_at_most_hourly_and_faster_while_backlogged(container):
    await add_policy(container, policy(limit=None, tokens=None))
    hour = PRUNE_INTERVAL_SECONDS
    ticks = iter([0.0, 10.0, hour - 1, hour, hour + 10, hour + RECONCILE_INTERVAL_SECONDS])
    full = AiUsagePruned(reservations=PRUNE_BATCH)
    ledger = _Recording(container, ticks, [AiUsagePruned(), full, AiUsagePruned()])
    await _admit(ledger)  # first admission prunes
    await _admit(ledger)
    await _admit(ledger)
    assert ledger.prunes == 1
    await _admit(ledger)  # an hour later, and the batch comes back full
    assert ledger.prunes == 2
    await _admit(ledger)
    assert ledger.prunes == 2
    await _admit(ledger)  # a backlog drains at the reconciliation pace
    assert ledger.prunes == 3


async def test_prune_failure_is_logged_without_detail_and_never_blocks_admission(container, caplog):
    await add_policy(container, policy(limit=None, tokens=None))
    ticks = iter([0.0, 1.0])
    ledger = _Recording(container, ticks, [RuntimeError("secret-bearing driver message")])
    with caplog.at_level(logging.WARNING, logger="ase.application.ai_usage"):
        await _admit(ledger)
        await _admit(ledger)
    assert ledger.prunes == 1
    [record] = [item for item in caplog.records if item.msg == "ai_usage.prune_failed"]
    assert record.error == "RuntimeError" and record.exc_info is None
    assert "secret-bearing" not in caplog.text


async def test_admission_tick_runs_the_real_prune(container):
    current = policy(limit=None, tokens=None)
    await add_policy(container, current)
    expired = await _reservation(container, current.id, "settled", RESERVATION_RETENTION * 2)
    await _admit(accounting(container))
    assert expired not in await _ids(container, AiUsageReservationRow)
