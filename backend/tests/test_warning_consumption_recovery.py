"""Independent connections exercise committed recovery and concurrent capacity."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence import warning_consumption
from ase.adapters.persistence.models import AlertRow
from ase.adapters.persistence.users import SqlUserRepository
from ase.adapters.persistence.warning import SqlWarningStore
from ase.adapters.persistence.warning_consumption_models import WarningConsumptionRow
from ase.application.warning.evaluator import evaluate_candidates
from ase.domain.warning import alert_from
from assistant_helpers import event
from report_job_api_helpers import job_settings
from test_consumed_alert_evidence import create_rule

__all__ = ["job_settings"]


async def test_lost_commit_acknowledgement_and_reopened_database_do_not_replay(
    container,
    user,
    clock,
    monkeypatch,
):
    rule = await create_rule(container, user)
    items = [replace(event(str(i)), published_at=clock.now()) for i in range(22)]
    container.store.upsert(items)
    original = AsyncSession.commit

    async def committed_then_interrupted(session):
        await original(session)
        raise OSError("synthetic lost acknowledgement")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", committed_then_interrupted)
        # Baseline sampling also commits; bypass it for this firing/recovery probe.
        firing = await evaluate_candidates(container.store, rule, clock.now(), None)
        assert firing is not None
        try:
            await SqlWarningStore(container.session_factory, container.access_policy).add_alert(
                alert_from(rule, firing, uuid4(), clock.now()),
                rule,
                consumed=firing.consumed,
            )
        except OSError:
            pass
        else:
            raise AssertionError("The synthetic lost acknowledgement was not reached")
    await container.engine.dispose()  # subsequent sessions reopen the on-disk database
    clock.advance(timedelta(minutes=6))
    assert await container.build_evaluator().run_once() == []
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AlertRow)) == 1
        assert (await session.get(WarningConsumptionRow, rule.id)).count == 22


async def test_competing_rules_cannot_overrun_global_capacity(container, user, clock, monkeypatch):
    rules = [await create_rule(container, user), await create_rule(container, user)]
    container.store.upsert([replace(event(str(i)), published_at=clock.now()) for i in range(2)])
    firings = [
        await evaluate_candidates(container.store, rule, clock.now(), None) for rule in rules
    ]
    monkeypatch.setattr(warning_consumption, "MAX_CONSUMED_TOTAL", 3)
    original = SqlUserRepository.lock_administration
    both_entered, release = asyncio.Event(), asyncio.Event()
    waiting = 0

    async def barrier(repository):
        nonlocal waiting
        waiting += 1
        if waiting == 2:
            both_entered.set()
        await release.wait()
        await original(repository)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", barrier)
    store = SqlWarningStore(container.session_factory, container.access_policy)
    tasks = [
        asyncio.create_task(
            store.add_alert(
                alert_from(rule, firing, uuid4(), clock.now()),
                rule,
                consumed=firing.consumed,
            )
        )
        for rule, firing in zip(rules, firings, strict=True)
    ]
    try:
        await asyncio.wait_for(both_entered.wait(), 5)
        release.set()
        outcomes = await asyncio.wait_for(asyncio.gather(*tasks), 5)
    finally:
        release.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    assert sorted(outcomes) == [False, True]
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AlertRow)) == 1
        assert await session.scalar(select(func.sum(WarningConsumptionRow.count))) == 2


async def test_stale_inflight_firing_cannot_reconsume_after_cooldown(container, user, clock):
    rule = await create_rule(container, user)
    container.store.upsert([replace(event(str(i)), published_at=clock.now()) for i in range(22)])
    firing = await evaluate_candidates(container.store, rule, clock.now(), None)
    assert firing is not None
    store = SqlWarningStore(container.session_factory, container.access_policy)
    assert await store.add_alert(
        alert_from(rule, firing, uuid4(), clock.now()), rule, consumed=firing.consumed
    )
    clock.advance(timedelta(minutes=6))
    assert not await store.add_alert(
        alert_from(rule, firing, uuid4(), clock.now()), rule, consumed=firing.consumed
    )
