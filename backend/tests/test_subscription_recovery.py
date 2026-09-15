"""Waiting or long-overdue subscriptions recover instead of wedging their cadence."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.container import Container
from ase.container.subscription_enqueue import SubscriptionAdmission
from ase.container.subscription_schedule_controls import control_schedule
from ase.domain.errors import RateLimited
from ase.domain.subscription_editions import EditionTrigger, EditionWorkflow
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted
from ase.domain.users import User
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from team_helpers import CONTEXT

CAPACITY = "ase.application.report_jobs.service.require_capacity"
BUDGET = "ase.container.report_jobs.require_admission_room"


def _input(**changes: object) -> ScheduleInput:
    data: dict[str, object] = {
        "name": "Recovering subscription",
        "template_id": "intsum",
        "country_iso": "UA",
        "timezone": "UTC",
        "local_hour": 6,
    }
    data.update(changes)
    return ScheduleInput(**data)  # type: ignore[arg-type]


async def _schedule(container: Container, user: User, **changes: object):
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    async with container.session_factory() as session:
        return await container.create_schedule(session).execute(user, _input(**changes), CONTEXT)


async def _history(container: Container, schedule_id):
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(schedule_id)
        current = await container.repositories(session).schedules.get(schedule_id)
    assert current is not None
    return editions, current


async def test_budget_blocked_slot_is_retried_and_cadence_resumes_next_month(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user)
    container.clock.advance(schedule.next_run_at - container.clock.now() + timedelta(minutes=1))
    with patch(BUDGET, side_effect=MonthlyBudgetExhausted()):
        assert await container.schedule_runner.run_once() == 0
        container.clock.advance(timedelta(minutes=10))
        assert await container.schedule_runner.run_once() == 0  # Retry delay not yet over.
        editions, _ = await _history(container, schedule.id)
        assert [item.workflow for item in editions] == [EditionWorkflow.BLOCKED]
        blocked_revision = editions[0].revision
        container.clock.advance(timedelta(hours=2))
        assert await container.schedule_runner.run_once() == 0
    editions, current = await _history(container, schedule.id)
    assert editions[0].workflow is EditionWorkflow.BLOCKED and editions[0].job_id is None
    assert editions[0].revision > blocked_revision
    assert current.next_run_at == schedule.next_run_at

    container.clock.advance(timedelta(days=40))
    assert await container.schedule_runner.run_once() == 1
    editions, current = await _history(container, schedule.id)
    queued = [item for item in editions if item.workflow is EditionWorkflow.QUEUED]
    assert len(queued) == 1 and queued[0].job_id is not None
    assert queued[0].due_at_utc is not None and queued[0].due_at_utc > schedule.next_run_at
    original = next(item for item in editions if item.due_at_utc == schedule.next_run_at)
    assert original.workflow is EditionWorkflow.SKIPPED
    assert current.next_run_at > container.clock.now()


async def test_manual_budget_block_is_retried_by_the_tick(container: Container, user: User) -> None:
    schedule = await _schedule(container, user)
    with patch(BUDGET, side_effect=MonthlyBudgetExhausted()):
        edition = await SubscriptionAdmission(container).run_now(
            schedule.id, uuid4(), user, CONTEXT, AsyncMock()
        )
    assert edition.workflow is EditionWorkflow.BLOCKED and edition.job_id is None
    container.clock.advance(timedelta(hours=2))
    assert container.clock.now() < schedule.next_run_at
    assert await container.schedule_runner.run_once() == 1
    editions, _ = await _history(container, schedule.id)
    assert [(item.trigger, item.workflow) for item in editions] == [
        (EditionTrigger.RUN_NOW, EditionWorkflow.QUEUED)
    ]


async def test_run_now_capacity_wait_is_retried_by_repeat_request(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user)
    admission = SubscriptionAdmission(container)
    request_id = uuid4()
    with patch(CAPACITY, side_effect=RateLimited(60)):
        waiting = await admission.run_now(schedule.id, request_id, user, CONTEXT, AsyncMock())
    assert waiting.workflow is EditionWorkflow.PENDING and waiting.job_id is None
    retried = await admission.run_now(schedule.id, request_id, user, CONTEXT, AsyncMock())
    assert retried.id == waiting.id
    assert retried.workflow is EditionWorkflow.QUEUED and retried.job_id is not None
    again = await admission.run_now(schedule.id, request_id, user, CONTEXT, AsyncMock())
    assert again == retried


async def test_run_now_capacity_wait_is_retried_by_the_tick(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user)
    with patch(CAPACITY, side_effect=RateLimited(60)):
        waiting = await SubscriptionAdmission(container).run_now(
            schedule.id, uuid4(), user, CONTEXT, AsyncMock()
        )
    container.clock.advance(timedelta(minutes=5))
    assert container.clock.now() < schedule.next_run_at
    assert await container.schedule_runner.run_once() == 1
    editions, _ = await _history(container, schedule.id)
    assert [(item.id, item.workflow) for item in editions] == [(waiting.id, EditionWorkflow.QUEUED)]


async def test_run_now_capacity_wait_never_blocks_the_scheduled_slot(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user)
    with patch(CAPACITY, side_effect=RateLimited(60)):
        waiting = await SubscriptionAdmission(container).run_now(
            schedule.id, uuid4(), user, CONTEXT, AsyncMock()
        )
    assert waiting.workflow is EditionWorkflow.PENDING and waiting.due_at_utc is None
    container.clock.advance(timedelta(days=3))
    assert await container.schedule_runner.run_once() == 1
    editions, current = await _history(container, schedule.id)
    manual = next(item for item in editions if item.id == waiting.id)
    queued = [item for item in editions if item.workflow is EditionWorkflow.QUEUED]
    assert manual.workflow is EditionWorkflow.SKIPPED
    assert len(queued) == 1 and queued[0].trigger is EditionTrigger.CATCH_UP
    assert manual.covered_by_edition_id == queued[0].id
    assert current.next_run_at > container.clock.now()


async def test_resume_after_more_than_a_year_paused_runs_latest_slot(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user)
    async with container.session_factory() as session:
        await control_schedule(
            container, session, user, schedule.id, False, CONTEXT, check_session=AsyncMock()
        )
    container.clock.advance(timedelta(days=400))
    async with container.session_factory() as session:
        resumed = await control_schedule(
            container, session, user, schedule.id, True, CONTEXT, check_session=AsyncMock()
        )
    now = container.clock.now()
    assert now - timedelta(days=1) < resumed.next_run_at <= now
    assert await container.schedule_runner.run_once() == 1
    _, current = await _history(container, schedule.id)
    assert current.next_run_at > now


async def test_definition_enable_after_long_pause_rebases_due_slot(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user, enabled=False)
    container.clock.advance(timedelta(days=400))
    async with container.session_factory() as session:
        edited = await container.update_schedule(session).execute(
            user, schedule.id, _input(), CONTEXT
        )
    now = container.clock.now()
    assert now - timedelta(days=1) < edited.next_run_at <= now
    assert await container.schedule_runner.run_once() == 1


async def test_enabled_schedule_far_behind_skips_ahead_instead_of_failing(
    container: Container, user: User
) -> None:
    schedule = await _schedule(container, user, cadence="weekly", weekday=2)
    container.clock.advance(timedelta(days=366 * 8))
    assert await container.schedule_runner.run_once() == 1
    editions, current = await _history(container, schedule.id)
    assert len(editions) == 1 and editions[0].workflow is EditionWorkflow.QUEUED
    assert editions[0].due_at_utc is not None
    assert container.clock.now() - editions[0].due_at_utc < timedelta(days=7)
    assert current.next_run_at > container.clock.now()
