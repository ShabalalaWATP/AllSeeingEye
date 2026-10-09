"""Schedule conversion retains links, terminal failures and archival boundaries."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.adapters.persistence.models import CollectionPlanRow, ScheduleRow
from ase.adapters.persistence.schedules import SqlScheduleStore
from ase.domain.collection import CollectionPlan, Pir
from ase.domain.errors import NotFound
from ase.domain.schedules import ScheduleErrorCode
from warning_scope_helpers import create_schedule


async def linked_schedule(container, user):
    now = container.clock.now()
    plan = CollectionPlan(
        uuid4(),
        "Scope",
        "",
        None,
        ("UA",),
        (Pir("P1", "What changed?"),),
        True,
        user.id,
        now,
        now,
    )
    original = await create_schedule(container, user, None)
    schedule = replace(original, plan_id=plan.id, next_run_at=now)
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        await repositories.plans.add(plan)
        await repositories.schedules.save(schedule)
        await session.commit()
    return schedule


@pytest.mark.parametrize("change", ["removed", "other_owner"])
async def test_loaded_plan_link_is_rechecked_before_background_publication(
    container, user, admin, change
):
    schedule = await linked_schedule(container, user)
    store = SqlScheduleStore(container.session_factory, container.access_policy)
    assert await store.can_run(schedule)
    assert await store.due(container.clock.now()) == [schedule]
    async with container.session_factory() as session:
        row = await session.get(CollectionPlanRow, schedule.plan_id)
        assert row is not None
        if change == "removed":
            # Retained legacy rows may outlive a removed linked plan.
            await session.delete(row)
        else:
            row.created_by = admin.id
        await session.commit()
    assert not await store.can_run(schedule)
    await store.mark_run(
        schedule.id,
        ran_at=container.clock.now(),
        next_run_at=container.clock.now() + timedelta(days=1),
        result=None,
        error_code=ScheduleErrorCode.PRODUCTION_FAILED,
        expected=schedule,
    )
    async with container.session_factory() as session:
        retained = await container.repositories(session).schedules.get(schedule.id)
    assert retained == schedule


async def test_failure_without_a_report_round_trips_through_the_due_store(container, user):
    schedule = await linked_schedule(container, user)
    store = SqlScheduleStore(container.session_factory, container.access_policy)
    now = container.clock.now()
    next_run = now + timedelta(days=1)
    await store.mark_run(
        schedule.id,
        ran_at=now,
        next_run_at=next_run,
        result=None,
        error_code=ScheduleErrorCode.PRODUCTION_FAILED,
        expected=schedule,
    )
    async with container.session_factory() as session:
        retained = await container.repositories(session).schedules.get(schedule.id)
    assert retained == replace(
        schedule,
        last_run_at=now,
        next_run_at=next_run,
        last_error=ScheduleErrorCode.PRODUCTION_FAILED,
    )
    assert await store.due(now) == []


@pytest.mark.parametrize("state", ["removed", "archived"])
async def test_saving_a_stale_snapshot_cannot_restore_a_removed_or_archived_schedule(
    container, user, state
):
    schedule = await create_schedule(container, user, None)
    async with container.session_factory() as session:
        row = await session.get(ScheduleRow, schedule.id)
        assert row is not None
        if state == "removed":
            await session.delete(row)
        else:
            row.archived_at = container.clock.now()
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await container.repositories(session).schedules.save(schedule)
        await session.rollback()
        row = await session.get(ScheduleRow, schedule.id)
        assert row is None if state == "removed" else row.archived_at == container.clock.now()
