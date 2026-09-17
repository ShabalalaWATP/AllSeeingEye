"""Due slots enter the durable report queue without running paid production inline."""

from datetime import timedelta
from unittest.mock import patch

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.container import Container
from ase.domain.errors import RateLimited
from ase.domain.subscription_editions import EditionWorkflow, scheduled_edition_id
from ase.domain.users import User
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from team_helpers import CONTEXT


async def _due_schedule(container: Container, owner: User):
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            owner,
            # Stated, so the cadence edit below is a real change of rhythm.
            ScheduleInput(
                name="Daily report", template_id="intsum", country_iso="UA", cadence="daily"
            ),
            CONTEXT,
        )
    container.clock.advance(schedule.next_run_at - container.clock.now() + timedelta(minutes=1))
    return schedule


async def test_due_schedule_admits_one_durable_job_before_any_report(
    container: Container, user: User
) -> None:
    schedule = await _due_schedule(container, user)
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        edition = await ledger.active(schedule.id)
        current = await container.repositories(session).schedules.get(schedule.id)
        assert edition is not None and current is not None
        assert edition.id == scheduled_edition_id(schedule.id, schedule.next_run_at)
        assert edition.workflow is EditionWorkflow.QUEUED
        assert edition.job_id is not None
        assert edition.report_id is None and edition.version_id is None
        assert current.next_run_at > schedule.next_run_at
        assert current.last_report_id is None
        job = await SqlReportJobRepository(session).get(edition.job_id)
        assert job is not None and job.status == "queued"
        assert job.request_key == edition.job_request_key
        assert await container.repositories(session).reports.get(job.report_id) is None
    assert await container.schedule_runner.run_once() == 0


async def test_capacity_wait_keeps_same_pending_slot_then_admits_it(
    container: Container, user: User
) -> None:
    schedule = await _due_schedule(container, user)
    with patch("ase.application.report_jobs.service.require_capacity", side_effect=RateLimited(60)):
        assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        pending = await ledger.active(schedule.id)
        current = await container.repositories(session).schedules.get(schedule.id)
        assert pending is not None and current is not None
        assert pending.workflow is EditionWorkflow.PENDING
        assert pending.safe_reason == "capacity_wait"
        assert pending.job_id is None
        assert current.next_run_at == schedule.next_run_at
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(schedule.id)
        assert len(editions) == 1
        assert editions[0].id == pending.id
        assert editions[0].workflow is EditionWorkflow.QUEUED
        assert editions[0].job_id is not None


async def test_pending_slot_keeps_frozen_due_time_after_cadence_edit(
    container: Container, user: User
) -> None:
    schedule = await _due_schedule(container, user)
    with patch("ase.application.report_jobs.service.require_capacity", side_effect=RateLimited(60)):
        assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        edited = await container.update_schedule(session).execute(
            user,
            schedule.id,
            ScheduleInput(
                name="Renamed weekly report",
                template_id="intsum",
                country_iso="UA",
                cadence="weekly",
                weekday=0,
            ),
            CONTEXT,
        )
    assert edited.next_run_at != schedule.next_run_at
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        editions = await ledger.history(schedule.id)
        current = await container.repositories(session).schedules.get(schedule.id)
        assert len(editions) == 1 and current is not None
        assert editions[0].due_at_utc == schedule.next_run_at
        assert editions[0].workflow is EditionWorkflow.QUEUED
        assert current.next_run_at == edited.next_run_at
