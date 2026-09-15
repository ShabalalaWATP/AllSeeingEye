"""Immutable subscription revisions and edition identities for durable scheduling."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid5

from ase.domain.report_jobs import job_error, job_timestamp
from ase.domain.subscription_snapshots import decode_snapshot

# Fixed forever: a job request key is derived from the stored edition UUID, never a caller UUID.
EDITION_JOB_NAMESPACE = UUID("4d63d4f8-463d-5b62-bf58-9e5d9761deaf")
SCHEDULED_EDITION_NAMESPACE = UUID("9ed5f65d-5cba-5ddc-8bc3-074fa3df0f13")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class EditionTrigger(StrEnum):
    SCHEDULED = "scheduled"
    CATCH_UP = "catch_up"
    RUN_NOW = "run_now"
    BASELINE = "baseline"


class EditionWorkflow(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


ACTIVE_WORKFLOWS = frozenset(
    {
        EditionWorkflow.PENDING,
        EditionWorkflow.QUEUED,
        EditionWorkflow.RUNNING,
        EditionWorkflow.RETRY_WAIT,
        EditionWorkflow.PAUSED,
        EditionWorkflow.BLOCKED,
    }
)


class EditionQuality(StrEnum):
    ABSENT = "absent"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class EditionCoverage(StrEnum):
    COMPLETE_FOR_PLAN = "complete_for_plan"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


def _digest(value: str) -> None:
    if not _DIGEST.fullmatch(value):
        raise ValueError("Use a SHA-256 compatibility fingerprint.")


def scheduled_edition_id(subscription_id: UUID, due_at_utc: datetime) -> UUID:
    """The same logical due slot always yields the same job admission key."""
    job_timestamp(due_at_utc)
    due = due_at_utc.astimezone(UTC)
    return uuid5(SCHEDULED_EDITION_NAMESPACE, f"{subscription_id}:{due.isoformat()}")


def manual_edition_id(subscription_id: UUID, trigger: EditionTrigger, request_id: UUID) -> UUID:
    """A caller UUID identifies one manual edition, independently of its observation time."""
    if trigger not in (EditionTrigger.RUN_NOW, EditionTrigger.BASELINE):
        raise ValueError("Manual edition identity requires a manual trigger.")
    return uuid5(SCHEDULED_EDITION_NAMESPACE, f"{subscription_id}:{trigger.value}:{request_id}")


@dataclass(frozen=True, slots=True)
class SubscriptionRevision:
    subscription_id: UUID
    revision: int
    owner_id: UUID
    team_id: UUID | None
    request_snapshot: str
    compatibility_fingerprint: str
    recurrence_policy: str
    collection_policy: str
    enabled: bool
    created_at: datetime
    brief_revision_id: UUID | None = None

    def __post_init__(self) -> None:
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("Subscription revisions must be positive.")
        job_timestamp(self.created_at)
        _digest(self.compatibility_fingerprint)
        if self.recurrence_policy not in {
            "legacy_utc_v1",
            "local_iana_v1",
        } or self.collection_policy not in {"rolling_snapshot_v1", "since_last_success_v1"}:
            raise ValueError("Unsupported subscription recurrence or collection policy.")
        if type(self.enabled) is not bool:
            raise ValueError("Subscription activation must be explicit.")
        decode_snapshot(self.request_snapshot)


@dataclass(frozen=True, slots=True)
class ObservationInterval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        job_timestamp(self.start)
        job_timestamp(self.end)
        if self.start >= self.end:
            raise ValueError("Observation intervals are half-open and non-empty.")


@dataclass(frozen=True, slots=True)
class SubscriptionEdition:
    id: UUID
    subscription_id: UUID
    trigger: EditionTrigger
    due_at_utc: datetime | None
    request_uuid: UUID | None
    frozen_revision: int
    requested: ObservationInterval
    effective_intervals: tuple[ObservationInterval, ...]
    gaps: tuple[ObservationInterval, ...]
    compatibility_fingerprint: str
    baseline_version_id: UUID | None
    workflow: EditionWorkflow
    report_quality: EditionQuality
    coverage: EditionCoverage
    created_at: datetime
    updated_at: datetime
    revision: int = 1
    job_id: UUID | None = None
    report_id: UUID | None = None
    version_id: UUID | None = None
    safe_reason: str | None = None
    covered_by_edition_id: UUID | None = None
    accepted_as_baseline: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.trigger, EditionTrigger)
            or not isinstance(self.workflow, EditionWorkflow)
            or not isinstance(self.report_quality, EditionQuality)
            or not isinstance(self.coverage, EditionCoverage)
        ):
            raise ValueError("Unknown edition trigger, workflow, quality or coverage state.")
        if self.trigger in (EditionTrigger.SCHEDULED, EditionTrigger.CATCH_UP):
            if self.due_at_utc is None or self.request_uuid is not None:
                raise ValueError("Scheduled editions require a due slot only.")
            job_timestamp(self.due_at_utc)
        elif self.due_at_utc is not None or self.request_uuid is None:
            raise ValueError("Manual editions require a request UUID only.")
        if type(self.frozen_revision) is not int or self.frozen_revision < 1:
            raise ValueError("Editions require a frozen positive subscription revision.")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("Edition fences must be positive.")
        job_timestamp(self.created_at)
        job_timestamp(self.updated_at)
        if self.updated_at < self.created_at:
            raise ValueError("Edition updates cannot precede creation.")
        _digest(self.compatibility_fingerprint)
        job_error(self.safe_reason)
        if type(self.accepted_as_baseline) is not bool or (
            self.accepted_as_baseline
            and (
                self.workflow is not EditionWorkflow.COMPLETED
                or self.report_quality not in {EditionQuality.READY, EditionQuality.NEEDS_REVIEW}
            )
        ):
            raise ValueError("Only a completed usable edition can be accepted as a baseline.")
        self._validate_result()
        for interval in (*self.effective_intervals, *self.gaps):
            if interval.start < self.requested.start or interval.end > self.requested.end:
                raise ValueError("Coverage intervals must fit within the requested interval.")

    def _validate_result(self) -> None:
        if (self.report_id is None) != (self.version_id is None):
            raise ValueError("An edition must pin both report and version IDs.")
        if self.report_quality is EditionQuality.ABSENT and self.report_id is not None:
            raise ValueError("An absent report cannot have a saved version.")
        if self.report_quality is not EditionQuality.ABSENT and self.report_id is None:
            raise ValueError("Report quality requires a saved version.")
        if (
            self.workflow is EditionWorkflow.COMPLETED
            and self.report_quality is EditionQuality.ABSENT
        ):
            raise ValueError("A completed edition requires a saved report version.")
        if (
            self.workflow in (EditionWorkflow.QUEUED, EditionWorkflow.RUNNING)
            and self.job_id is None
        ):
            raise ValueError("Queued and running editions require a durable report job.")
        if self.covered_by_edition_id is not None and (
            self.workflow is not EditionWorkflow.SKIPPED or self.covered_by_edition_id == self.id
        ):
            raise ValueError("Only a skipped edition can link its covering edition.")

    @property
    def job_request_key(self) -> UUID:
        return uuid5(EDITION_JOB_NAMESPACE, str(self.id))

    @property
    def logical_payload(self) -> tuple[object, ...]:
        return (
            self.subscription_id,
            self.trigger,
            self.due_at_utc,
            self.request_uuid,
            self.frozen_revision,
            self.requested,
            self.compatibility_fingerprint,
            self.baseline_version_id,
        )


@dataclass(frozen=True, slots=True)
class SubscriptionLineage:
    subscription_id: UUID
    compatibility_fingerprint: str
    analytical_baseline_version_id: UUID | None
    covered_intervals: tuple[ObservationInterval, ...]
    complete_cutoff: datetime | None
    updated_at: datetime
    revision: int = 1

    def __post_init__(self) -> None:
        _digest(self.compatibility_fingerprint)
        job_timestamp(self.updated_at)
        if self.complete_cutoff is not None:
            job_timestamp(self.complete_cutoff)
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("Lineage revisions must be positive.")
        if self.complete_cutoff is not None and not self.covered_intervals:
            raise ValueError("A complete cutoff requires covered intervals.")


@dataclass(frozen=True, slots=True)
class EditionAttempt:
    id: UUID
    edition_id: UUID
    job_id: UUID | None
    number: int
    stage: str
    started_at: datetime
    ended_at: datetime | None
    outcome: str
    next_retry_at: datetime | None
    lease_token: UUID | None
    job_revision: int | None
    reserved_requests: int = 0
    actual_requests: int = 0
    reserved_output_tokens: int = 0
    actual_output_tokens: int = 0

    def __post_init__(self) -> None:
        if type(self.number) is not int or self.number < 1:
            raise ValueError("Edition attempts must have positive numbers.")
        for value in (
            self.reserved_requests,
            self.actual_requests,
            self.reserved_output_tokens,
            self.actual_output_tokens,
        ):
            if type(value) is not int or not 0 <= value <= 10_000_000:
                raise ValueError("Edition usage counters must be bounded non-negative integers.")
        job_timestamp(self.started_at)
        if self.ended_at is not None:
            job_timestamp(self.ended_at)
            if self.ended_at < self.started_at:
                raise ValueError("An attempt cannot end before it starts.")
        if self.next_retry_at is not None:
            job_timestamp(self.next_retry_at)
        job_error(self.stage)
        job_error(self.outcome)
        if self.job_revision is not None and self.job_revision < 1:
            raise ValueError("Attempt job fences must be positive.")


@dataclass(frozen=True, slots=True)
class EditionDelivery:
    id: UUID
    edition_id: UUID
    channel: str
    destination_ref: UUID | None
    event_kind: str
    idempotency_key: UUID
    state: str
    attempts: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        for value in (self.channel, self.event_kind, self.state):
            job_error(value)
        if type(self.attempts) is not int or not 0 <= self.attempts <= 100:
            raise ValueError("Delivery attempts must be bounded.")
        job_timestamp(self.created_at)
        job_timestamp(self.updated_at)
        if self.updated_at < self.created_at:
            raise ValueError("Delivery updates cannot precede creation.")
