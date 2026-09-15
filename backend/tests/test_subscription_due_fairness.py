"""Bounded due pages rotate across owners and retain every overdue identity."""

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.schedules import SqlScheduleStore
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.container import subscription_due_tick
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
)
from helpers import create_user
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from team_helpers import CONTEXT


async def _overdue_schedules(container, heavy_owner, other_owner):
    identities = []
    for owner, number in ((heavy_owner, 5), (other_owner, 1)):
        for index in range(number):
            async with container.session_factory() as session:
                schedule = await container.create_schedule(session).execute(
                    owner,
                    ScheduleInput(
                        name=f"Due {owner.id} {index}",
                        template_id="intsum",
                        country_iso="UA",
                    ),
                    CONTEXT,
                )
            identities.append(schedule.id)
    now = container.clock.now()
    async with container.session_factory() as session:
        for identity in identities:
            row = await session.get(ScheduleRow, identity)
            assert row is not None
            row.next_run_at = now - timedelta(days=2 if row.created_by == heavy_owner.id else 1)
        await session.commit()
    return identities


async def test_due_schedule_pages_are_owner_fair_bounded_and_wrap_without_loss(
    container, user
) -> None:
    other = await create_user(
        container, email="fair-owner@example.com", password="another-long-passphrase"
    )
    identities = set(await _overdue_schedules(container, user, other))
    store = SqlScheduleStore(container.session_factory, container.access_policy)
    now = container.clock.now()
    first, cursor = await store.due_batch(now, limit=2)
    assert len(first) == 2
    assert {item.created_by for item in first} == {user.id, other.id}
    seen = {item.id for item in first}
    for _ in range(2):
        page, cursor = await store.due_batch(now, limit=2, cursor=cursor)
        assert len(page) == 2
        seen.update(item.id for item in page)
    assert seen == identities
    restarted, _ = await store.due_batch(now, limit=2)
    assert {item.id for item in restarted} == {item.id for item in first}


async def test_pending_edition_pages_rotate_across_owners_and_preserve_slots(
    container, user
) -> None:
    other = await create_user(
        container, email="fair-pending@example.com", password="another-long-passphrase"
    )
    schedule_ids = await _overdue_schedules(container, user, other)
    now = container.clock.now()
    async with container.session_factory() as session:
        repository = SqlSubscriptionEditionRepository(session)
        for schedule_id in schedule_ids:
            schedule = await container.repositories(session).schedules.get(schedule_id)
            assert schedule is not None
            frozen = await repository.add_revision(revision_from_schedule(schedule, 1))
            await repository.reserve(
                SubscriptionEdition(
                    id=uuid4(),
                    subscription_id=schedule.id,
                    trigger=EditionTrigger.SCHEDULED,
                    due_at_utc=schedule.next_run_at,
                    request_uuid=None,
                    frozen_revision=1,
                    requested=ObservationInterval(
                        schedule.next_run_at - timedelta(days=1), schedule.next_run_at
                    ),
                    effective_intervals=(),
                    gaps=(),
                    compatibility_fingerprint=frozen.compatibility_fingerprint,
                    baseline_version_id=None,
                    workflow=EditionWorkflow.PENDING,
                    report_quality=EditionQuality.ABSENT,
                    coverage=EditionCoverage.UNKNOWN,
                    created_at=now,
                    updated_at=now,
                )
            )
        await session.commit()
    async with container.session_factory() as session:
        repository = SqlSubscriptionEditionRepository(session)
        first, cursor = await repository.due_batch(now, limit=2)
        assert len(first) == 2
        assert {owner for _, owner in first} == {user.id, other.id}
        seen: set[UUID] = {edition.subscription_id for edition, _ in first}
        for _ in range(2):
            page, cursor = await repository.due_batch(now, limit=2, cursor=cursor)
            assert len(page) == 2
            seen.update(edition.subscription_id for edition, _ in page)
        assert seen == set(schedule_ids)
        assert len(await repository.due(now, limit=10)) == 6


async def test_overlapping_bounded_ticks_keep_every_slot_or_due_row(
    container, user, monkeypatch
) -> None:
    other = await create_user(
        container, email="fair-concurrent@example.com", password="another-long-passphrase"
    )
    schedule_ids = await _overdue_schedules(container, user, other)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    monkeypatch.setattr(subscription_due_tick, "SCHEDULE_DUE_LIMIT", 2)
    monkeypatch.setattr(subscription_due_tick, "PENDING_DUE_LIMIT", 2)
    now = container.clock.now()
    await asyncio.gather(container.schedule_runner.run_once(), container.schedule_runner.run_once())
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        admitted_owners = set()
        job_ids = set()
        for schedule_id in schedule_ids:
            current = await container.repositories(session).schedules.get(schedule_id)
            assert current is not None
            editions = await ledger.history(schedule_id)
            if any(edition.job_id is not None for edition in editions):
                admitted_owners.add(current.created_by)
            job_ids.update(edition.job_id for edition in editions if edition.job_id is not None)
            if current.next_run_at > now:
                assert editions, "Cadence advanced without a durable due-slot edition."
            if not editions:
                assert current.next_run_at <= now, "An unadmitted due row disappeared."
            assert len({edition.due_at_utc for edition in editions}) == len(editions)
        assert admitted_owners == {user.id, other.id}
        assert len(job_ids) <= 4
