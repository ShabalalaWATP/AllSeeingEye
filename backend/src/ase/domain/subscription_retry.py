"""Versioned, side-effect-free retry decisions for one durable subscription edition.

The caller classifies failures after checking the job's saved call reservations and
applies decisions under the existing edition/job revision fences. This policy never
creates a fresh edition, resets a job budget or resolves an uncertain paid call.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from enum import StrEnum
from uuid import UUID

from ase.domain.report_jobs import job_timestamp

POLICY_VERSION = "subscription-retry-v1"
RETRY_DELAYS = (timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=2))
RETRY_HORIZON = timedelta(hours=24)
CAPACITY_DELAY = timedelta(minutes=1)
MAX_JITTER_SECONDS = 30
_DELTA_SECONDS = re.compile(r"[0-9]{1,10}\Z")


class RetryFailure(StrEnum):
    TRANSIENT_PRE_DISPATCH = "transient_pre_dispatch"
    RETRYABLE_RESPONSE = "retryable_response"
    SOURCE_FAILURE = "source_failure"
    AUTHENTICATION = "authentication"
    SCOPE_REVOKED = "scope_revoked"
    CAPABILITY_MISSING = "capability_missing"
    UNCERTAIN_PAID_CALL = "uncertain_paid_call"
    EXPIRED_ACTIVE_CALL_LEASE = "expired_active_call_lease"
    VALIDATION = "validation"
    QUEUE_CAPACITY = "queue_capacity"
    JOB_BUDGET = "job_budget"
    MONTHLY_BUDGET = "monthly_budget"
    PERMANENT = "permanent"


class RetryAction(StrEnum):
    RETRY_WAIT = "retry_wait"
    CAPACITY_WAIT = "capacity_wait"
    QUALITY_GATE = "quality_gate"
    REPAIR_CHECKPOINT = "repair_checkpoint"
    PAUSE_FOR_RESUME = "pause_for_resume"
    BLOCK = "block"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class RetryContext:
    edition_id: UUID
    failure: RetryFailure
    failed_attempt: int
    first_failed_at: datetime
    now: datetime
    retry_after: str | None = None
    budget_available: bool = True
    saved_draft: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.edition_id, UUID) or not isinstance(self.failure, RetryFailure):
            raise ValueError("Retry decisions require an edition and known failure class.")
        if type(self.failed_attempt) is not int or not 1 <= self.failed_attempt <= 10_000:
            raise ValueError("A failed attempt must have a bounded positive number.")
        job_timestamp(self.first_failed_at)
        job_timestamp(self.now)
        if self.now < self.first_failed_at:
            raise ValueError("Retry decisions cannot precede the first failure.")
        object.__setattr__(self, "first_failed_at", self.first_failed_at.astimezone(UTC))
        object.__setattr__(self, "now", self.now.astimezone(UTC))
        if self.retry_after is not None and type(self.retry_after) is not str:
            raise ValueError("Retry-After must be header text when supplied.")
        if type(self.budget_available) is not bool or type(self.saved_draft) is not bool:
            raise ValueError("Retry budget and checkpoint flags must be explicit booleans.")


@dataclass(frozen=True, slots=True)
class RetryDecision:
    action: RetryAction
    reason: str
    next_retry_at: datetime | None = None
    policy_version: str = POLICY_VERSION


def _jitter(edition_id: UUID, failed_attempt: int) -> timedelta:
    # A stable per-edition and per-attempt spread, never Python's process-random hash.
    digest = hashlib.sha256(edition_id.bytes + failed_attempt.to_bytes(4, "big")).digest()
    return timedelta(seconds=digest[0] % (MAX_JITTER_SECONDS + 1))


def _retry_after_deadline(value: str | None, now: datetime) -> datetime | None:
    if value is None or len(value) > 128 or any(char in value for char in "\r\n"):
        return None
    header = value.strip()
    if _DELTA_SECONDS.fullmatch(header):
        return now + timedelta(seconds=int(header))
    try:
        parsed = parsedate_to_datetime(header)
    except (IndexError, TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def decide_retry(context: RetryContext) -> RetryDecision:  # noqa: PLR0911, PLR0912
    """Return the next safe action; failed_attempt=1 is the initial attempt."""
    failure = context.failure
    if failure in {RetryFailure.UNCERTAIN_PAID_CALL, RetryFailure.EXPIRED_ACTIVE_CALL_LEASE}:
        return RetryDecision(RetryAction.PAUSE_FOR_RESUME, "uncertain_paid_outcome")
    if failure in {
        RetryFailure.AUTHENTICATION,
        RetryFailure.SCOPE_REVOKED,
        RetryFailure.CAPABILITY_MISSING,
    }:
        return RetryDecision(RetryAction.BLOCK, failure.value)
    if failure in {RetryFailure.JOB_BUDGET, RetryFailure.MONTHLY_BUDGET}:
        return RetryDecision(RetryAction.BLOCK, failure.value)
    if failure is RetryFailure.SOURCE_FAILURE:
        return RetryDecision(RetryAction.QUALITY_GATE, "source_failure_coverage")
    if failure is RetryFailure.PERMANENT:
        return RetryDecision(RetryAction.FAIL, "permanent_failure")
    if not context.budget_available:
        return RetryDecision(RetryAction.BLOCK, "budget_unavailable")
    if failure is RetryFailure.QUEUE_CAPACITY:
        return RetryDecision(
            RetryAction.CAPACITY_WAIT,
            "queue_capacity",
            context.now + CAPACITY_DELAY + _jitter(context.edition_id, 0),
        )
    if failure is RetryFailure.VALIDATION:
        return RetryDecision(
            RetryAction.REPAIR_CHECKPOINT if context.saved_draft else RetryAction.QUALITY_GATE,
            "validation_checkpoint" if context.saved_draft else "validation_without_checkpoint",
        )
    if context.failed_attempt > len(RETRY_DELAYS):
        return RetryDecision(RetryAction.FAIL, "retry_attempts_exhausted")
    horizon = context.first_failed_at + RETRY_HORIZON
    if context.now >= horizon:
        return RetryDecision(RetryAction.FAIL, "retry_horizon_exhausted")
    deadline = (
        context.now
        + RETRY_DELAYS[context.failed_attempt - 1]
        + _jitter(context.edition_id, context.failed_attempt)
    )
    if failure is RetryFailure.RETRYABLE_RESPONSE:
        retry_after = _retry_after_deadline(context.retry_after, context.now)
        if retry_after is not None:
            deadline = max(deadline, retry_after)
    if deadline > horizon:
        return RetryDecision(RetryAction.FAIL, "retry_horizon_exhausted")
    return RetryDecision(
        RetryAction.RETRY_WAIT, "known_transient_failure", deadline.astimezone(UTC)
    )
