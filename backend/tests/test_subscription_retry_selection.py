"""Inactive subscriptions cannot consume the bounded automatic-retry queue."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.domain.subscription_editions import EditionWorkflow
from test_subscription_retry_pause import _state, _waiting


@pytest.mark.parametrize("archived", [False, True])
async def test_twenty_inactive_waits_cannot_starve_enabled_retry(container, user, archived):
    schedule, edition, original, retry = await _waiting(container, user)
    waiting, job, attempt = await _state(container, edition.id, original.id)
    assert attempt.next_retry_at is not None
    inactive = []
    async with container.session_factory() as session:
        schedules = container.repositories(session).schedules
        ledger = SqlSubscriptionEditionRepository(session)
        jobs = SqlReportJobRepository(session)
        frozen = await ledger.get_revision(schedule.id, waiting.frozen_revision)
        assert frozen is not None
        for _ in range(20):
            disabled = replace(
                schedule,
                id=uuid4(),
                enabled=False,
                archived_at=container.clock.now() if archived else None,
            )
            await schedules.add(disabled)
            await ledger.add_revision(replace(frozen, subscription_id=disabled.id))
            retained = replace(
                job, id=uuid4(), request_key=uuid4(), report_id=uuid4(), version_id=uuid4()
            )
            await jobs.add(retained)
            old_wait = replace(
                waiting, id=uuid4(), subscription_id=disabled.id, job_id=retained.id, revision=2
            )
            await ledger.reserve(
                replace(old_wait, workflow=EditionWorkflow.PENDING, job_id=None, revision=1)
            )
            assert await ledger.advance(old_wait, expected_revision=1) is not None
            await ledger.add_attempt(
                replace(
                    attempt,
                    id=uuid4(),
                    edition_id=old_wait.id,
                    job_id=retained.id,
                    next_retry_at=attempt.next_retry_at - timedelta(seconds=1),
                )
            )
            inactive.append((old_wait.id, retained.id))
        await session.commit()

    await retry.resume_due()
    admitted, current, _ = await _state(container, edition.id, original.id)
    assert admitted.workflow is EditionWorkflow.QUEUED and current.status == "queued"
    for edition_id, job_id in inactive:
        retained, paused, _ = await _state(container, edition_id, job_id)
        assert retained.workflow is EditionWorkflow.RETRY_WAIT and paused.status == "paused"
