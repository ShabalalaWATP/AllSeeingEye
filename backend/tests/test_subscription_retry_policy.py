"""Offline decisions for bounded subscription retries and uncertain paid work."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from email.utils import format_datetime
from uuid import UUID

import pytest

from ase.domain.subscription_retry import (
    CAPACITY_DELAY,
    MAX_JITTER_SECONDS,
    POLICY_VERSION,
    RETRY_DELAYS,
    RetryAction,
    RetryContext,
    RetryFailure,
    decide_retry,
)

EDITION_ID = UUID("f42e7969-a306-4fe8-96d6-83fece5ae335")
FIRST_FAILURE = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def context(failure: RetryFailure, **changes: object) -> RetryContext:
    return RetryContext(
        edition_id=EDITION_ID,
        failure=failure,
        failed_attempt=1,
        first_failed_at=FIRST_FAILURE,
        now=FIRST_FAILURE,
        **changes,
    )


@pytest.mark.parametrize("attempt,delay", tuple(enumerate(RETRY_DELAYS, 1)))
@pytest.mark.parametrize(
    "failure", [RetryFailure.TRANSIENT_PRE_DISPATCH, RetryFailure.RETRYABLE_RESPONSE]
)
def test_transient_retries_use_three_stable_jittered_backoffs(
    attempt: int, delay: timedelta, failure: RetryFailure
) -> None:
    first = decide_retry(replace(context(failure), failed_attempt=attempt))
    repeated = decide_retry(replace(context(failure), failed_attempt=attempt))
    assert first == repeated
    assert first.action is RetryAction.RETRY_WAIT
    assert first.reason == "known_transient_failure"
    assert first.policy_version == POLICY_VERSION
    assert first.next_retry_at is not None
    assert (
        delay
        <= first.next_retry_at - FIRST_FAILURE
        <= delay + timedelta(seconds=MAX_JITTER_SECONDS)
    )


def test_fourth_failure_and_horizon_end_are_terminal() -> None:
    exhausted = decide_retry(replace(context(RetryFailure.RETRYABLE_RESPONSE), failed_attempt=4))
    assert exhausted.action is RetryAction.FAIL
    assert exhausted.reason == "retry_attempts_exhausted"
    late = decide_retry(
        replace(
            context(RetryFailure.TRANSIENT_PRE_DISPATCH),
            now=FIRST_FAILURE + timedelta(hours=23, minutes=59),
        )
    )
    assert late.action is RetryAction.FAIL
    assert late.reason == "retry_horizon_exhausted"
    assert late.next_retry_at is None


def test_retry_after_seconds_and_http_date_only_extend_the_deadline() -> None:
    by_seconds = decide_retry(context(RetryFailure.RETRYABLE_RESPONSE, retry_after="900"))
    assert by_seconds.next_retry_at == FIRST_FAILURE + timedelta(minutes=15)
    later = FIRST_FAILURE + timedelta(minutes=45)
    by_date = decide_retry(
        context(RetryFailure.RETRYABLE_RESPONSE, retry_after=format_datetime(later, usegmt=True))
    )
    assert by_date.next_retry_at == later
    short = decide_retry(context(RetryFailure.RETRYABLE_RESPONSE, retry_after="1"))
    assert (
        short.next_retry_at == decide_retry(context(RetryFailure.RETRYABLE_RESPONSE)).next_retry_at
    )
    invalid = decide_retry(context(RetryFailure.RETRYABLE_RESPONSE, retry_after="invalid\r\nX: 1"))
    assert invalid.next_retry_at == short.next_retry_at
    assert "invalid" not in invalid.reason


def test_retry_after_beyond_horizon_does_not_schedule_early_work() -> None:
    result = decide_retry(context(RetryFailure.RETRYABLE_RESPONSE, retry_after="90000"))
    assert result.action is RetryAction.FAIL
    assert result.reason == "retry_horizon_exhausted"
    assert result.next_retry_at is None


def test_decisions_normalise_local_timestamps_to_utc() -> None:
    local = FIRST_FAILURE.astimezone(timezone(timedelta(hours=1)))
    original = replace(
        context(RetryFailure.TRANSIENT_PRE_DISPATCH), first_failed_at=local, now=local
    )
    assert original.first_failed_at == FIRST_FAILURE
    assert original.first_failed_at.tzinfo is UTC
    assert decide_retry(original).next_retry_at.tzinfo is UTC
    waiting = decide_retry(replace(original, failure=RetryFailure.QUEUE_CAPACITY))
    assert waiting.next_retry_at and waiting.next_retry_at.tzinfo is UTC


@pytest.mark.parametrize(
    "failure",
    [
        RetryFailure.AUTHENTICATION,
        RetryFailure.SCOPE_REVOKED,
        RetryFailure.CAPABILITY_MISSING,
    ],
)
def test_auth_scope_and_capability_block_without_periodic_retry(failure: RetryFailure) -> None:
    result = decide_retry(context(failure))
    assert result.action is RetryAction.BLOCK
    assert result.reason == failure.value
    assert result.next_retry_at is None


@pytest.mark.parametrize(
    "failure", [RetryFailure.UNCERTAIN_PAID_CALL, RetryFailure.EXPIRED_ACTIVE_CALL_LEASE]
)
def test_uncertain_paid_outcomes_require_explicit_resume_even_when_budget_is_gone(
    failure: RetryFailure,
) -> None:
    result = decide_retry(replace(context(failure), budget_available=False))
    assert result.action is RetryAction.PAUSE_FOR_RESUME
    assert result.reason == "uncertain_paid_outcome"
    assert result.next_retry_at is None


def test_capacity_wait_is_distinct_from_a_budget_block() -> None:
    waiting = decide_retry(context(RetryFailure.QUEUE_CAPACITY))
    assert waiting.action is RetryAction.CAPACITY_WAIT
    assert waiting.next_retry_at is not None
    assert (
        CAPACITY_DELAY
        <= waiting.next_retry_at - FIRST_FAILURE
        <= CAPACITY_DELAY + timedelta(seconds=MAX_JITTER_SECONDS)
    )
    assert waiting == decide_retry(context(RetryFailure.QUEUE_CAPACITY))
    blocked = decide_retry(replace(context(RetryFailure.QUEUE_CAPACITY), budget_available=False))
    assert blocked.action is RetryAction.BLOCK
    assert blocked.next_retry_at is None
    for failure in (RetryFailure.JOB_BUDGET, RetryFailure.MONTHLY_BUDGET):
        result = decide_retry(context(failure))
        assert result.action is RetryAction.BLOCK
        assert result.reason == failure.value


def test_known_source_and_validation_failures_use_existing_quality_or_checkpoint_paths() -> None:
    source = decide_retry(context(RetryFailure.SOURCE_FAILURE))
    assert source.action is RetryAction.QUALITY_GATE
    assert source.next_retry_at is None
    repair = decide_retry(replace(context(RetryFailure.VALIDATION), saved_draft=True))
    assert repair.action is RetryAction.REPAIR_CHECKPOINT
    missing_draft = decide_retry(context(RetryFailure.VALIDATION))
    assert missing_draft.action is RetryAction.QUALITY_GATE
    no_budget = decide_retry(
        replace(context(RetryFailure.VALIDATION), saved_draft=True, budget_available=False)
    )
    assert no_budget.action is RetryAction.BLOCK
    assert decide_retry(context(RetryFailure.PERMANENT)).action is RetryAction.FAIL


@pytest.mark.parametrize(
    "changes",
    [
        {"failed_attempt": True},
        {"failed_attempt": 0},
        {"first_failed_at": FIRST_FAILURE.replace(tzinfo=None)},
        {"now": FIRST_FAILURE - timedelta(seconds=1)},
        {"failure": "provider_error"},
        {"budget_available": 1},
        {"saved_draft": "yes"},
    ],
)
def test_invalid_inputs_cannot_enter_the_retry_policy(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(context(RetryFailure.RETRYABLE_RESPONSE), **changes)
