"""Application retry policy owns eligibility, lock order and all-or-nothing fences."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.schedules.subscription_retry import SubscriptionRetry
from ase.domain.subscription_editions import EditionWorkflow
from test_subscription_publication import NOW, edition


class RetryDependencies:
    def __init__(self):
        self.order = []
        self.edition = replace(
            edition(uuid4(), NOW - timedelta(days=1), NOW),
            workflow=EditionWorkflow.RETRY_WAIT,
        )
        self.job = SimpleNamespace(
            id=self.edition.job_id,
            owner_id=uuid4(),
            status="paused",
            error="known_transient_failure",
            revision=3,
            payload={
                "calls": [],
                "sections": {},
                "budget": {"max_requests": 4, "max_output_tokens": 1000},
            },
        )
        self.attempt = SimpleNamespace(outcome="known_transient_failure", next_retry_at=NOW)
        self.session = SimpleNamespace(
            due_retry_ids=AsyncMock(return_value=[self.edition.id]),
            lock_administration=AsyncMock(side_effect=lambda: self.order.append("administration")),
            editions=SimpleNamespace(
                get=AsyncMock(return_value=self.edition),
                advance=AsyncMock(return_value=self.edition),
            ),
            schedules=SimpleNamespace(
                get=AsyncMock(return_value=SimpleNamespace(enabled=True, archived_at=None))
            ),
            jobs=SimpleNamespace(
                get=AsyncMock(return_value=self.job), resume=AsyncMock(return_value=self.job)
            ),
            latest_attempt=AsyncMock(return_value=self.attempt),
            first_failure_at=AsyncMock(return_value=NOW - timedelta(minutes=6)),
            require_admission_room=AsyncMock(),
            stop_waiting=AsyncMock(return_value=True),
            commit=AsyncMock(),
            rollback=AsyncMock(),
        )

    @asynccontextmanager
    async def transactions(self):
        yield self.session

    @asynccontextmanager
    async def guard(self):
        self.order.append("source")
        yield

    async def run(self):
        await SubscriptionRetry(
            self.transactions, SimpleNamespace(now=lambda: NOW), self.guard
        ).resume_due()


@pytest.mark.parametrize("reason", ["not_due", "disabled", "archived", "unknown_usage"])
async def test_waiting_retry_rechecks_current_eligibility(reason):
    deps = RetryDependencies()
    if reason == "not_due":
        deps.attempt.next_retry_at = NOW + timedelta(seconds=1)
    elif reason in {"disabled", "archived"}:
        deps.session.schedules.get.return_value = SimpleNamespace(
            enabled=reason != "disabled", archived_at=NOW if reason == "archived" else None
        )
    else:
        deps.job.payload["calls"] = [{"status": "uncertain"}]
    await deps.run()
    assert deps.order == ["source", "administration"]
    deps.session.jobs.resume.assert_not_awaited()
    if reason == "unknown_usage":
        deps.session.stop_waiting.assert_awaited_once_with(
            deps.edition, deps.job, EditionWorkflow.PAUSED, "retry_checkpoint_unavailable", NOW
        )
    else:
        deps.session.commit.assert_not_awaited()


async def test_expired_horizon_persists_only_when_both_fences_succeed():
    deps = RetryDependencies()
    deps.session.first_failure_at.return_value = NOW - timedelta(days=1)
    deps.session.stop_waiting.return_value = False
    await deps.run()
    deps.session.jobs.resume.assert_not_awaited()
    deps.session.commit.assert_not_awaited()
    deps.session.rollback.assert_awaited_once()
