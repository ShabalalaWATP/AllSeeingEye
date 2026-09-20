"""Schedule pauses fence retry timers and keep their retained job resumable."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_retry_attempts import due_retry_ids, latest_attempt
from ase.container.subscription_retry_orchestration import SubscriptionRetryOrchestrator
from ase.container.subscription_schedule_controls import control_schedule
from ase.domain.subscription_editions import EditionWorkflow
from team_helpers import CONTEXT
from test_subscription_retry_worker import _claim, _queued


async def _waiting(container, user):
    schedule, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    retry = SubscriptionRetryOrchestrator(container)
    await retry.pause(claimed, "provider_error", ConnectionError("synthetic pre-dispatch failure"))
    async with container.session_factory() as session:
        attempt = await latest_attempt(session, edition.id)
    assert attempt is not None and attempt.next_retry_at is not None
    container.clock.advance(attempt.next_retry_at - container.clock.now() + timedelta(seconds=1))
    return schedule, edition, original, retry


async def _toggle(container, user, schedule_id, enabled):
    async with container.session_factory() as session:
        return await control_schedule(
            container, session, user, schedule_id, enabled, CONTEXT, check_session=AsyncMock()
        )


async def _state(container, edition_id, job_id):
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        edition = await ledger.get(edition_id)
        job = await SqlReportJobRepository(session).get(job_id)
        attempts = await ledger.attempts(edition_id)
    assert edition is not None and job is not None and attempts
    return edition, job, attempts[-1]


async def test_pause_retry_wait_then_resume_keeps_checkpoint_and_attempt_history(container, user):
    schedule, edition, original, retry = await _waiting(container, user)
    _, waiting_job, previous_attempt = await _state(container, edition.id, original.id)
    await _toggle(container, user, schedule.id, False)
    await retry.resume_due()
    paused, job, attempt = await _state(container, edition.id, original.id)
    assert paused.workflow is EditionWorkflow.PAUSED
    assert paused.safe_reason == "schedule_paused"
    assert job.status == "paused" and job.payload == waiting_job.payload
    assert attempt == previous_attempt

    await _toggle(container, user, schedule.id, True)
    resumed, job, attempt = await _state(container, edition.id, original.id)
    assert resumed.workflow is EditionWorkflow.QUEUED and job.status == "queued"
    assert job.payload == waiting_job.payload
    assert job.report_id == original.report_id and job.request_key == original.request_key
    assert attempt == previous_attempt
    await _claim(container, edition.id, original.id)
    _, _, second = await _state(container, edition.id, original.id)
    assert second.number == 2


async def test_pause_wins_after_retry_timer_has_selected_edition(container, user):
    schedule, edition, original, retry = await _waiting(container, user)
    selected, release = asyncio.Event(), asyncio.Event()

    async def selected_before_pause(session, now):
        identifiers = await due_retry_ids(session, now)
        selected.set()
        await release.wait()
        return identifiers

    with patch(
        "ase.container.subscription_retry_orchestration.due_retry_ids", selected_before_pause
    ):
        timer = asyncio.create_task(retry.resume_due())
        try:
            await asyncio.wait_for(selected.wait(), timeout=5)
            await _toggle(container, user, schedule.id, False)
            release.set()
            await asyncio.wait_for(timer, timeout=5)
        finally:
            release.set()
            timer.cancel()
            await asyncio.gather(timer, return_exceptions=True)
    paused, job, _ = await _state(container, edition.id, original.id)
    assert paused.workflow is EditionWorkflow.PAUSED and job.status == "paused"
    assert paused.safe_reason == "schedule_paused"
    await _toggle(container, user, schedule.id, True)
    resumed, job, _ = await _state(container, edition.id, original.id)
    assert resumed.workflow is EditionWorkflow.QUEUED and job.status == "queued"


async def test_pause_also_wins_when_timer_has_already_requeued(container, user):
    schedule, edition, original, retry = await _waiting(container, user)
    await retry.resume_due()
    await _toggle(container, user, schedule.id, False)
    paused, job, _ = await _state(container, edition.id, original.id)
    assert paused.workflow is EditionWorkflow.PAUSED and job.status == "paused"
    assert paused.safe_reason == "schedule_paused"
    await _toggle(container, user, schedule.id, True)
    resumed, job, _ = await _state(container, edition.id, original.id)
    assert resumed.workflow is EditionWorkflow.QUEUED and job.status == "queued"


async def test_retry_requeue_and_pause_share_guard_until_transaction_finishes(container, user):
    schedule, edition, original, retry = await _waiting(container, user)
    resuming, release = asyncio.Event(), asyncio.Event()
    resume = SqlReportJobRepository.resume

    async def wait_before_resume(repository, *args, **kwargs):
        resuming.set()
        await release.wait()
        return await resume(repository, *args, **kwargs)

    with patch.object(SqlReportJobRepository, "resume", wait_before_resume):
        timer = asyncio.create_task(retry.resume_due())
        pause = None
        try:
            await asyncio.wait_for(resuming.wait(), timeout=5)
            pause = asyncio.create_task(_toggle(container, user, schedule.id, False))
            await asyncio.sleep(0)
            assert not pause.done()
            release.set()
            await asyncio.wait_for(asyncio.gather(timer, pause), timeout=5)
        finally:
            release.set()
            tasks = [timer] if pause is None else [timer, pause]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    paused, job, _ = await _state(container, edition.id, original.id)
    assert paused.workflow is EditionWorkflow.PAUSED and job.status == "paused"
    assert paused.safe_reason == "schedule_paused"


async def test_retry_timer_does_not_admit_retained_wait_on_disabled_schedule(container, user):
    schedule, edition, original, retry = await _waiting(container, user)
    # Old saved state or the schedule-edit API can disable an existing retry wait.
    async with container.session_factory() as session:
        await container.repositories(session).schedules.save(replace(schedule, enabled=False))
        await session.commit()
    await retry.resume_due()
    waiting, job, _ = await _state(container, edition.id, original.id)
    assert waiting.workflow is EditionWorkflow.RETRY_WAIT and job.status == "paused"
