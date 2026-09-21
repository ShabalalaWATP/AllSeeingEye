"""Scheduled and manual subscriptions share their owner's research allowance."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.container import Container
from ase.container.subscription_enqueue import SubscriptionAdmission
from ase.domain.errors import RateLimited
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted
from ase.domain.users import User
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from team_helpers import CONTEXT


async def _schedule(container: Container, user: User):
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    async with container.session_factory() as session:
        return await container.create_schedule(session).execute(
            user,
            ScheduleInput(
                name="Quota recovery",
                template_id="intsum",
                country_iso="UA",
                cadence="daily",
                timezone="UTC",
                local_hour=6,
            ),
            CONTEXT,
        )


async def _allowance(container: Container, user: User):
    async with container.session_factory() as session:
        return await container.research_usage(session).me(user)


async def _exhaust(container: Container, user: User):
    allowance = await _allowance(container, user)
    for _ in range(allowance.remaining):
        async with container.session_factory() as session:
            await container.research_usage(session).admit(user, None)
    return await _allowance(container, user)


async def _assign(container: Container, admin: User, user: User, tier: int):
    previous = await _allowance(container, user)
    async with container.session_factory() as session:
        return await container.research_usage(session).assign(
            admin, user.id, tier, previous.revision, CONTEXT
        )


async def _history(container: Container, schedule_id):
    async with container.session_factory() as session:
        return await SqlSubscriptionEditionRepository(session).history(schedule_id)


async def test_due_quota_block_is_durable_and_does_not_charge_or_prepare_on_every_tick(
    container: Container,
    user: User,
) -> None:
    schedule = await _schedule(container, user)
    container.clock.advance(schedule.next_run_at - container.clock.now())
    exhausted = await _exhaust(container, user)
    assert await container.schedule_runner.run_once() == 0
    [blocked] = await _history(container, schedule.id)
    assert blocked.workflow is EditionWorkflow.BLOCKED
    assert blocked.safe_reason == "research_usage_limit"
    assert blocked.job_id is None
    with patch(
        "ase.application.report_jobs.service.ReportJobService.prepare_candidate",
        side_effect=AssertionError("An exhausted allowance must not prepare another job."),
    ) as prepare:
        for seconds in (0, 60, 240, 1, 1):
            container.clock.advance(timedelta(seconds=seconds))
            assert await container.schedule_runner.run_once() == 0
        prepare.assert_not_called()
    [retried] = await _history(container, schedule.id)
    assert retried.workflow is EditionWorkflow.BLOCKED and retried.job_id is None
    assert retried.safe_reason == "research_usage_limit"
    assert retried.revision == blocked.revision + 1
    assert (await _allowance(container, user)).used == exhausted.used


@pytest.mark.parametrize("tier", [3, 5])
async def test_manual_subscription_recovers_after_upgrade_before_old_weekly_reset(
    container: Container,
    user: User,
    admin: User,
    tier: int,
) -> None:
    schedule = await _schedule(container, user)
    exhausted = await _exhaust(container, user)
    blocked = await SubscriptionAdmission(container).run_now(
        schedule.id, uuid4(), user, CONTEXT, AsyncMock()
    )
    assert blocked.workflow is EditionWorkflow.BLOCKED
    await _assign(container, admin, user, tier)
    container.clock.advance(timedelta(minutes=5))
    assert container.clock.now() < exhausted.resets_at
    assert container.clock.now() < schedule.next_run_at
    assert await container.schedule_runner.run_once() == 1
    [queued] = await _history(container, schedule.id)
    assert queued.id == blocked.id and queued.workflow is EditionWorkflow.QUEUED
    assert queued.safe_reason is None and queued.job_id is not None
    assert (await _allowance(container, user)).used == exhausted.used + 1
    assert await container.schedule_runner.run_once() == 0
    assert (await _allowance(container, user)).used == exhausted.used + 1


async def test_daily_reset_reopens_blocked_manual_subscription(
    container: Container,
    user: User,
    admin: User,
) -> None:
    schedule = await _schedule(container, user)
    await _assign(container, admin, user, 2)
    exhausted = await _exhaust(container, user)
    blocked = await SubscriptionAdmission(container).run_now(
        schedule.id, uuid4(), user, CONTEXT, AsyncMock()
    )
    container.clock.advance(exhausted.resets_at - container.clock.now())
    assert await container.schedule_runner.run_once() == 1
    [queued] = await _history(container, schedule.id)
    assert queued.id == blocked.id and queued.workflow is EditionWorkflow.QUEUED
    assert (await _allowance(container, user)).used == 1


async def test_weekly_reset_coalesces_old_blocked_slots_into_one_latest_due_run(
    container: Container,
    user: User,
) -> None:
    schedule = await _schedule(container, user)
    container.clock.advance(schedule.next_run_at - container.clock.now())
    exhausted = await _exhaust(container, user)
    assert await container.schedule_runner.run_once() == 0
    [blocked] = await _history(container, schedule.id)
    container.clock.advance(exhausted.resets_at - container.clock.now())
    assert await container.schedule_runner.run_once() == 1
    history = await _history(container, schedule.id)
    original = next(item for item in history if item.id == blocked.id)
    queued = [item for item in history if item.workflow is EditionWorkflow.QUEUED]
    assert len(queued) == 1
    assert original.workflow is EditionWorkflow.SKIPPED
    assert original.covered_by_edition_id == queued[0].id
    assert (await _allowance(container, user)).used == 1


async def test_repeated_manual_request_recovers_same_edition_after_upgrade(
    container: Container,
    user: User,
    admin: User,
) -> None:
    schedule = await _schedule(container, user)
    await _exhaust(container, user)
    request_id = uuid4()
    service = SubscriptionAdmission(container)
    blocked = await service.run_now(schedule.id, request_id, user, CONTEXT, AsyncMock())
    assert blocked.workflow is EditionWorkflow.BLOCKED
    assert await service.run_now(schedule.id, request_id, user, CONTEXT, AsyncMock()) == blocked
    await _assign(container, admin, user, 3)
    container.clock.advance(timedelta(minutes=5))
    queued = await service.run_now(schedule.id, request_id, user, CONTEXT, AsyncMock())
    assert queued.id == blocked.id and queued.workflow is EditionWorkflow.QUEUED
    assert (await _allowance(container, user)).used == 5
    assert await service.run_now(schedule.id, request_id, user, CONTEXT, AsyncMock()) == queued
    assert (await _allowance(container, user)).used == 5


async def test_admin_run_now_spends_owner_allowance_once_and_preserves_admin_allowance(
    container: Container,
    user: User,
    admin: User,
) -> None:
    schedule = await _schedule(container, user)
    request_id = uuid4()
    service = SubscriptionAdmission(container)
    first = await service.run_now(schedule.id, request_id, admin, CONTEXT, AsyncMock())
    repeated = await service.run_now(schedule.id, request_id, admin, CONTEXT, AsyncMock())
    assert first.workflow is EditionWorkflow.QUEUED and repeated == first
    assert (await _allowance(container, user)).used == 1
    assert (await _allowance(container, admin)).used == 0


@pytest.mark.parametrize(
    ("target", "error", "workflow", "reason"),
    [
        (
            "ase.application.report_jobs.service.require_capacity",
            RateLimited(60),
            EditionWorkflow.PENDING,
            "capacity_wait",
        ),
        (
            "ase.container.report_jobs.require_admission_room",
            MonthlyBudgetExhausted(),
            EditionWorkflow.BLOCKED,
            "monthly_budget_exhausted",
        ),
    ],
)
async def test_capacity_and_monthly_budget_blocks_retain_their_policy_without_quota_charge(
    container: Container,
    user: User,
    target,
    error,
    workflow,
    reason,
) -> None:
    schedule = await _schedule(container, user)
    with patch(target, side_effect=error):
        blocked = await SubscriptionAdmission(container).run_now(
            schedule.id, uuid4(), user, CONTEXT, AsyncMock()
        )
    assert blocked.workflow is workflow and blocked.safe_reason == reason
    assert blocked.job_id is None
    assert (await _allowance(container, user)).used == 0
    container.clock.advance(timedelta(hours=1))
    assert await container.schedule_runner.run_once() == 1
    assert (await _allowance(container, user)).used == 1
