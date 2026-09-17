"""Recovered section failures keep their reason across subscription attempt records."""

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_retry_attempts import latest_attempt
from ase.container.subscription_retry_orchestration import SubscriptionRetryOrchestrator
from ase.domain.subscription_editions import EditionWorkflow
from test_report_job_failure_recovery import known_failure_payload
from test_subscription_retry_worker import _claim, _in_flight_call, _queued


@pytest.mark.parametrize("uncertain", [False, True])
async def test_expired_subscription_failure_preserves_confirmed_reason_without_retry(
    container, user, uncertain
):
    _, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    payload = deepcopy(claimed.payload)
    payload.update(known_failure_payload())
    payload["calls"] = [
        _in_flight_call()
        | {
            "status": "uncertain" if uncertain else "completed",
            "error": "interrupted" if uncertain else None,
            "prompt_tokens": 20,
            "completion_tokens": 30,
        }
    ]
    async with container.session_factory() as session:
        updated = await SqlReportJobRepository(session).checkpoint(
            original.id,
            expected_revision=claimed.revision,
            lease_token=claimed.lease_token,
            payload=payload,
            stage="drafting",
            now=container.clock.now(),
        )
        assert updated is not None
        await session.commit()
    container.clock.advance(timedelta(seconds=46))
    await container.report_job_worker.tick()
    async with container.session_factory() as session:
        stopped = await SqlSubscriptionEditionRepository(session).get(edition.id)
        job = await SqlReportJobRepository(session).get(original.id)
        attempt = await latest_attempt(session, edition.id)
    reason = "uncertain_paid_outcome" if uncertain else "section_invalid_section"
    assert stopped.workflow is EditionWorkflow.PAUSED
    assert job.status == "paused"
    assert job.error == ("interrupted_uncertain" if uncertain else reason)
    assert stopped.safe_reason == attempt.outcome == reason
    assert attempt.ended_at is not None and attempt.next_retry_at is None
    assert job.payload == payload
    container.clock.advance(timedelta(days=2))
    await SubscriptionRetryOrchestrator(container).resume_due()
    async with container.session_factory() as session:
        assert await SqlReportJobRepository(session).queued() == []


@pytest.mark.parametrize(
    ("workflow", "status", "error"),
    [
        (EditionWorkflow.PAUSED, "paused", None),
        (EditionWorkflow.RUNNING, "queued", None),
        (EditionWorkflow.RUNNING, "paused", "model_changed"),
    ],
)
async def test_reconciliation_does_not_overwrite_controls_after_candidate_selection(
    container, user, workflow, status, error
):
    _, edition, job = await _queued(container, user)
    # The candidate query saw a running edition and paused job. Explicit controls
    # commit before either fresh read, so that initial state is no longer current.
    edition = replace(edition, workflow=workflow)
    job = replace(job, status=status, error=error)
    editions = SimpleNamespace(
        get=AsyncMock(return_value=edition), advance=AsyncMock(return_value=None)
    )
    jobs = SimpleNamespace(get=AsyncMock(return_value=job))
    session = AsyncMock()
    session.scalars.return_value = [edition.id]
    with (
        patch(
            "ase.container.subscription_retry_orchestration.SqlSubscriptionEditionRepository",
            return_value=editions,
        ),
        patch(
            "ase.container.subscription_retry_orchestration.SqlReportJobRepository",
            return_value=jobs,
        ),
    ):
        await SubscriptionRetryOrchestrator(container).recover_expired_editions(
            session, container.clock.now()
        )
    editions.advance.assert_not_called()
