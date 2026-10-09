"""Capacity, corruption and failed commits must never consume only part of a firing."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence import warning_consumption, warning_store
from ase.adapters.persistence.models import AlertRow
from ase.adapters.persistence.warning_consumption_models import WarningConsumptionRow
from ase.domain import warning
from ase.domain.consumed_evidence import CONSUMED_RETENTION, MAGIC, decode
from assistant_helpers import event
from test_consumed_alert_evidence import create_rule


async def counts(container, rule):
    async with container.session_factory() as session:
        alerts = await session.scalar(select(func.count()).select_from(AlertRow))
        consumed = await session.get(WarningConsumptionRow, rule.id)
        return alerts, None if consumed is None else consumed.count


@pytest.mark.parametrize("boundary", ["evaluation", "rule", "global"])
async def test_capacity_defers_whole_firing_with_operational_reason(
    container,
    user,
    clock,
    monkeypatch,
    caplog,
    boundary,
):
    rule = await create_rule(container, user)
    if boundary == "evaluation":
        monkeypatch.setattr(warning, "MAX_CONSUMED_PER_RULE", 2)
    else:
        name = "MAX_CONSUMED_PER_RULE" if boundary == "rule" else "MAX_CONSUMED_TOTAL"
        monkeypatch.setattr(warning_consumption, name, 2)
    container.store.upsert([replace(event(str(i)), published_at=clock.now()) for i in range(3)])
    assert await container.build_evaluator().run_once() == []
    assert await counts(container, rule) == (0, None)
    assert any(
        "consumed_evidence_capacity" in getattr(record, "reason", "") for record in caplog.records
    )


async def test_existing_capacity_is_retained_then_released_only_after_expiry(
    container,
    user,
    clock,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(warning_consumption, "MAX_CONSUMED_TOTAL", 3)
    first = await create_rule(container, user)
    container.store.upsert([replace(event(str(i)), published_at=clock.now()) for i in range(2)])
    assert len(await container.build_evaluator().run_once()) == 1
    second = await create_rule(container, user)
    assert await container.build_evaluator().run_once() == []
    assert await counts(container, first) == (1, 2)
    assert await counts(container, second) == (1, None)
    assert any(
        getattr(record, "reason", None) == "global_consumed_evidence_capacity"
        for record in caplog.records
    )

    clock.advance(CONSUMED_RETENTION)
    await container.build_evaluator().run_once()
    assert await counts(container, first) == (1, 2)  # inclusive lower window edge
    clock.advance(timedelta(microseconds=1))
    await container.build_evaluator().run_once()
    assert await counts(container, first) == (1, None)


async def test_notification_failure_rolls_back_alert_and_all_consumption(
    container, user, clock, monkeypatch
):
    rule = await create_rule(container, user)
    container.store.upsert([replace(event(str(i)), published_at=clock.now()) for i in range(22)])
    original = warning_store.enqueue_alert_notifications

    async def fail(*args, **kwargs):
        raise RuntimeError("synthetic transaction failure")

    monkeypatch.setattr(warning_store, "enqueue_alert_notifications", fail)
    with pytest.raises(RuntimeError, match="synthetic transaction failure"):
        await container.build_evaluator().run_once()
    assert await counts(container, rule) == (0, None)
    monkeypatch.setattr(warning_store, "enqueue_alert_notifications", original)
    assert len(await container.build_evaluator().run_once()) == 1
    assert await counts(container, rule) == (1, 22)


async def test_corrupt_consumption_defers_instead_of_replaying(container, user, clock, caplog):
    rule = await create_rule(container, user)
    container.store.upsert([replace(event(str(i)), published_at=clock.now()) for i in range(22)])
    assert len(await container.build_evaluator().run_once()) == 1
    async with container.session_factory() as session:
        row = await session.get(WarningConsumptionRow, rule.id)
        assert row is not None and len(decode(row.data, row.count)) == 22
        row.data = MAGIC[:-1] + b"\xff" + row.data[len(MAGIC) :]
        await session.commit()
    clock.advance(timedelta(minutes=6))
    assert await container.build_evaluator().run_once() == []
    assert await counts(container, rule) == (1, 22)
    assert any(
        getattr(record, "reason", None) == "invalid_consumed_evidence" for record in caplog.records
    )
