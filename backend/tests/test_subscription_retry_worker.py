"""Retried subscription attempts keep one edition, job and paid-call ledger."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_retry_attempts import (
    first_failure_at,
    latest_attempt,
    start_attempt,
)
from ase.application.report_jobs.controls import resumed_payload
from ase.application.schedules.manage import ScheduleInput
from ase.container.subscription_retry_orchestration import SubscriptionRetryOrchestrator
from ase.domain.subscription_editions import EditionWorkflow
from feeds_helpers import make_event
from llm_fixture_helpers import seed_legacy_profile
from team_helpers import CONTEXT


def _in_flight_call() -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "status": "in_flight",
        "request_hash": "a" * 64,
        "schema": "report_section",
        "model": "fixture-model",
        "profile_id": None,
        "reserved_output": 100,
        "prompt_tokens": None,
        "completion_tokens": None,
        "latency_ms": 0.0,
        "error": None,
    }


async def _queued(container, user):
    await seed_legacy_profile(
        container,
        {
            "name": "Retry fixture profile",
            "base_url": "https://model.test/v1",
            "model": "fixture-model",
            "api_key": "synthetic-job-key",
            "roles": ["assessment"],
            "max_output_tokens": 32000,
            "temperature": 0.1,
        },
    )
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            user,
            ScheduleInput(name="Retry fixture", template_id="intsum", country_iso="UA"),
            CONTEXT,
        )
    container.clock.advance(schedule.next_run_at - container.clock.now() + timedelta(minutes=1))
    container.store.upsert(
        tuple(
            make_event(
                f"retry-{index}",
                source_id="usgs_earthquakes",
                title=f"Instrument observation {index}",
                country_iso="UA",
                published_at=container.clock.now(),
                observed_at=container.clock.now(),
            )
            for index in range(4)
        )
    )
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        edition = (await SqlSubscriptionEditionRepository(session).history(schedule.id))[0]
        job = await SqlReportJobRepository(session).get(edition.job_id)
        schedule = await container.repositories(session).schedules.get(schedule.id)
    assert schedule is not None and job is not None
    assert edition.workflow is EditionWorkflow.QUEUED
    return schedule, edition, job


async def _claim(container, edition_id, job_id):
    now = container.clock.now()
    async with container.session_factory() as session:
        jobs = SqlReportJobRepository(session)
        editions = SqlSubscriptionEditionRepository(session)
        job = await jobs.get(job_id)
        edition = await editions.get(edition_id)
        assert job is not None and edition is not None
        claimed = await jobs.claim(
            job.id,
            expected_revision=job.revision,
            lease_token=uuid4(),
            now=now,
            lease_until=now + timedelta(seconds=45),
        )
        assert claimed is not None
        assert await editions.advance(
            replace(
                edition,
                workflow=EditionWorkflow.RUNNING,
                updated_at=now,
                revision=edition.revision + 1,
            ),
            expected_revision=edition.revision,
        )
        await start_attempt(session, edition, claimed, now)
        await session.commit()
    return claimed


async def test_known_transient_retry_reuses_job_then_uncertain_call_stays_paused(
    container, user
) -> None:
    schedule, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    retry = SubscriptionRetryOrchestrator(container)
    await retry.pause(claimed, "provider_error", ConnectionError("private transport detail"))
    async with container.session_factory() as session:
        waiting = await SqlSubscriptionEditionRepository(session).get(edition.id)
        paused = await SqlReportJobRepository(session).get(original.id)
        attempt = await latest_attempt(session, edition.id)
        current_schedule = await container.repositories(session).schedules.get(schedule.id)
    assert waiting is not None and paused is not None and attempt is not None
    assert current_schedule is not None
    assert waiting.workflow is EditionWorkflow.RETRY_WAIT
    assert waiting.safe_reason == paused.error == attempt.outcome == "known_transient_failure"
    assert attempt.next_retry_at is not None
    assert attempt.number == 1 and attempt.ended_at is not None
    assert current_schedule.next_run_at == schedule.next_run_at
    assert "private transport detail" not in waiting.safe_reason
    await retry.resume_due()
    async with container.session_factory() as session:
        assert (await SqlReportJobRepository(session).get(original.id)).status == "paused"
    container.clock.advance(attempt.next_retry_at - container.clock.now() + timedelta(seconds=1))
    await retry.resume_due()
    async with container.session_factory() as session:
        queued = await SqlReportJobRepository(session).get(original.id)
        again = await SqlSubscriptionEditionRepository(session).get(edition.id)
    assert queued is not None and again is not None
    assert queued.status == "queued" and again.workflow is EditionWorkflow.QUEUED
    assert queued.request_key == original.request_key
    assert queued.report_id == original.report_id and queued.version_id == original.version_id
    assert queued.payload == original.payload

    claimed_again = await _claim(container, edition.id, original.id)
    payload = deepcopy(claimed_again.payload)
    payload.setdefault("calls", []).append(_in_flight_call())
    async with container.session_factory() as session:
        saved = await SqlReportJobRepository(session).checkpoint(
            original.id,
            expected_revision=claimed_again.revision,
            lease_token=claimed_again.lease_token,
            payload=payload,
            stage="drafting",
            now=container.clock.now(),
        )
        assert saved is not None
        await session.commit()
    await retry.pause(claimed_again, "provider_error", RuntimeError("private provider detail"))
    async with container.session_factory() as session:
        stopped = await SqlSubscriptionEditionRepository(session).get(edition.id)
        stopped_job = await SqlReportJobRepository(session).get(original.id)
        second = await latest_attempt(session, edition.id)
    assert stopped is not None and stopped_job is not None and second is not None
    assert stopped.workflow is EditionWorkflow.PAUSED
    assert stopped.safe_reason == stopped_job.error == second.outcome == "uncertain_paid_outcome"
    assert second.next_retry_at is None and second.number == 2
    assert second.reserved_requests == 1 and second.actual_requests == 0
    assert second.reserved_output_tokens == 100
    container.clock.advance(timedelta(days=2))
    await retry.resume_due()
    async with container.session_factory() as session:
        stopped = await SqlSubscriptionEditionRepository(session).get(edition.id)
    assert stopped is not None and stopped.workflow is EditionWorkflow.PAUSED


async def test_retry_attempts_exhaust_without_a_new_job_or_edition(container, user) -> None:
    schedule, edition, original = await _queued(container, user)
    retry = SubscriptionRetryOrchestrator(container)
    for number in range(1, 5):
        claimed = await _claim(container, edition.id, original.id)
        await retry.pause(claimed, "provider_error", ConnectionError("private transport detail"))
        async with container.session_factory() as session:
            current_edition = await SqlSubscriptionEditionRepository(session).get(edition.id)
            current_job = await SqlReportJobRepository(session).get(original.id)
            attempt = await latest_attempt(session, edition.id)
            current_schedule = await container.repositories(session).schedules.get(schedule.id)
        assert current_edition is not None and current_job is not None and attempt is not None
        assert current_schedule is not None and current_schedule.next_run_at == schedule.next_run_at
        assert attempt.number == number and attempt.ended_at is not None
        assert current_job.request_key == original.request_key
        if number < 4:
            assert current_edition.workflow is EditionWorkflow.RETRY_WAIT
            assert attempt.next_retry_at is not None
            container.clock.advance(attempt.next_retry_at - container.clock.now())
            await retry.resume_due()
        else:
            assert current_edition.workflow is EditionWorkflow.FAILED
            assert current_job.status == "failed"
            assert attempt.outcome == "retry_attempts_exhausted"
            assert attempt.next_retry_at is None


async def test_expired_retry_horizon_does_not_dispatch(container, user) -> None:
    _, edition, original = await _queued(container, user)
    retry = SubscriptionRetryOrchestrator(container)
    claimed = await _claim(container, edition.id, original.id)
    await retry.pause(claimed, "provider_error", ConnectionError())
    container.clock.advance(timedelta(days=2))
    await retry.resume_due()
    async with container.session_factory() as session:
        exhausted = await SqlSubscriptionEditionRepository(session).get(edition.id)
        stopped = await SqlReportJobRepository(session).get(original.id)
        attempt = await latest_attempt(session, edition.id)
    assert exhausted is not None and stopped is not None and attempt is not None
    assert exhausted.workflow is EditionWorkflow.FAILED
    assert exhausted.safe_reason == stopped.error == "retry_horizon_exhausted"
    assert stopped.status == "failed" and attempt.number == 1


async def test_expired_active_lease_closes_attempt_as_uncertain(container, user) -> None:
    _, edition, original = await _queued(container, user)
    await _claim(container, edition.id, original.id)
    container.clock.advance(timedelta(seconds=46))
    await container.report_job_worker.tick()
    async with container.session_factory() as session:
        stopped = await SqlSubscriptionEditionRepository(session).get(edition.id)
        job = await SqlReportJobRepository(session).get(original.id)
        attempt = await latest_attempt(session, edition.id)
    assert stopped is not None and job is not None and attempt is not None
    assert stopped.workflow is EditionWorkflow.PAUSED
    assert stopped.safe_reason == attempt.outcome == "uncertain_paid_outcome"
    assert job.status == "paused" and job.error == "interrupted_uncertain"
    assert attempt.ended_at is not None and attempt.next_retry_at is None


async def test_worker_claim_records_attempt_and_generic_provider_error_pauses(
    container, user
) -> None:
    _, edition, original = await _queued(container, user)
    worker = container.report_job_worker
    with patch.object(worker, "process", new_callable=AsyncMock) as run:
        await worker.tick()
        await asyncio.sleep(0)
        run.assert_awaited_once()
    async with container.session_factory() as session:
        claimed = await SqlReportJobRepository(session).get(original.id)
        attempt = await latest_attempt(session, edition.id)
    assert claimed is not None and attempt is not None
    assert claimed.status == "running" and attempt.number == 1
    assert attempt.outcome == "running" and attempt.lease_token == claimed.lease_token
    await SubscriptionRetryOrchestrator(container).pause(
        claimed, "provider_error", RuntimeError("private provider detail")
    )
    async with container.session_factory() as session:
        paused = await SqlSubscriptionEditionRepository(session).get(edition.id)
        job = await SqlReportJobRepository(session).get(original.id)
        attempt = await latest_attempt(session, edition.id)
    assert paused is not None and job is not None and attempt is not None
    assert paused.workflow is EditionWorkflow.PAUSED
    assert paused.safe_reason == job.error == attempt.outcome == "provider_error"
    assert attempt.next_retry_at is None
    await worker.stop()


async def test_immediate_operator_resume_closes_old_attempt_before_new_claim(
    container, user
) -> None:
    _, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    payload = deepcopy(claimed.payload)
    payload.setdefault("calls", []).append(_in_flight_call())
    async with container.session_factory() as session:
        jobs = SqlReportJobRepository(session)
        editions = SqlSubscriptionEditionRepository(session)
        saved = await jobs.checkpoint(
            original.id,
            expected_revision=claimed.revision,
            lease_token=claimed.lease_token,
            payload=payload,
            stage="drafting",
            now=container.clock.now(),
        )
        assert saved is not None
        paused = await jobs.pause(
            original.id,
            expected_revision=saved.revision,
            now=container.clock.now(),
            error="operator_paused",
        )
        assert paused is not None
        current = await editions.get(edition.id)
        assert current is not None
        assert await editions.advance(
            replace(
                current,
                workflow=EditionWorkflow.PAUSED,
                safe_reason="operator_paused",
                revision=current.revision + 1,
            ),
            expected_revision=current.revision,
        )
        await session.commit()
    async with container.session_factory() as session:
        jobs = SqlReportJobRepository(session)
        editions = SqlSubscriptionEditionRepository(session)
        paused = await jobs.get(original.id)
        current = await editions.get(edition.id)
        assert paused is not None and current is not None
        resumed = await jobs.resume(
            original.id,
            expected_revision=paused.revision,
            now=container.clock.now(),
            payload=resumed_payload(paused),
        )
        assert resumed is not None
        assert await editions.advance(
            replace(
                current,
                workflow=EditionWorkflow.QUEUED,
                safe_reason=None,
                revision=current.revision + 1,
            ),
            expected_revision=current.revision,
        )
        await session.commit()
    worker = container.report_job_worker
    with patch.object(worker, "process", new_callable=AsyncMock):
        await worker.tick()
    async with container.session_factory() as session:
        job = await SqlReportJobRepository(session).get(original.id)
        attempts = await SqlSubscriptionEditionRepository(session).attempts(edition.id)
        first_retry_failure = await first_failure_at(session, edition.id)
    assert job is not None and job.status == "running"
    assert job.payload["calls"][0]["status"] == "uncertain"
    assert len(attempts) == 2
    assert attempts[0].number == 1 and attempts[0].outcome == "uncertain_paid_outcome"
    assert attempts[0].ended_at is not None and attempts[0].reserved_requests == 1
    assert attempts[1].number == 2 and attempts[1].ended_at is None
    assert first_retry_failure is None
    await worker.stop()
