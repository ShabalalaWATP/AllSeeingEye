"""Administrator evaluation runs over packaged synthetic cases.

A run calls one saved AI connection for a selected subset of fixed-packet cases.
Its figures are deterministic structural checks and usage, never accuracy: the
cases are assistant-authored and await human validation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmProvider, ReasoningEffort

# The fixed-packet ``intrep`` pipeline: up to two drafting calls (a validation retry),
# then one analysis call and one entailment check.
CALLS_PER_CASE = 4
MAX_RUN_CALLS = 200
MAX_RUN_CASES = 40
MAX_CASE_ID_LENGTH = 80
RETAINED_RUNS = 20
# Every reserved call and recorded case renews the lease. An expired lease means the
# owning process stopped without finishing the run, so another start may replace it.
RUN_LEASE = timedelta(minutes=15)
ESTIMATE_NOTICE = (
    "Estimate only: selected cases multiplied by the usual calls per case. The call cap "
    "is enforced; failed and retried calls count towards it."
)
RESULT_NOTICE = (
    "Synthetic cases with assistant-authored rubrics, pending human validation. "
    "Deterministic structural checks only; not accuracy, factual correctness or "
    "readiness for publication."
)


class EvaluationRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


class EvaluationStopReason(StrEnum):
    CALL_CAP = "call_cap"
    ALLOWANCE = "allowance_limit"
    CONNECTION_CHANGED = "connection_changed"
    ACCESS_REVOKED = "access_revoked"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class EvaluationCaseInfo:
    id: str
    casebook: str
    title: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class EvaluationEstimate:
    cases: int
    calls_per_case: int = CALLS_PER_CASE

    @property
    def calls(self) -> int:
        return self.cases * self.calls_per_case


@dataclass(frozen=True, slots=True)
class EvaluationConnection:
    """Public request settings of a saved connection. Never holds its key."""

    profile_id: UUID
    name: str
    model: str
    base_url: str = field(repr=False)
    provider: LlmProvider
    max_output_tokens: int
    temperature: float
    reasoning_effort: ReasoningEffort | None


CheckValue = int | float | bool | None


@dataclass(frozen=True, slots=True)
class EvaluationCaseSummary:
    """One finished case: its fingerprint, report status and structural checks."""

    case_id: str
    fingerprint: str
    report_status: str
    model_calls: int
    checks: Mapping[str, CheckValue]
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(slots=True)
class EvaluationRun:
    id: UUID
    actor_id: UUID | None
    profile_id: UUID
    profile_name: str
    model: str
    profile_fingerprint: str = field(repr=False)
    case_ids: tuple[str, ...]
    case_fingerprints: Mapping[str, str]
    max_calls: int
    status: EvaluationRunStatus
    created_at: datetime
    lease_expires_at: datetime | None
    stop_reason: EvaluationStopReason | None = None
    cancel_requested: bool = False
    calls_reserved: int = 0
    calls_failed: int = 0
    results: tuple[EvaluationCaseSummary, ...] = ()
    finished_at: datetime | None = None
    has_artefact: bool = False

    @property
    def active(self) -> bool:
        return self.status is EvaluationRunStatus.RUNNING

    @property
    def estimate(self) -> EvaluationEstimate:
        return EvaluationEstimate(len(self.case_ids))

    def lease_expired(self, now: datetime) -> bool:
        return self.active and (self.lease_expires_at is None or self.lease_expires_at <= now)


def selected_cases(
    requested: list[str], catalogue: tuple[EvaluationCaseInfo, ...]
) -> tuple[EvaluationCaseInfo, ...]:
    """Validate a selection against the packaged catalogue, keeping catalogue order."""
    if not requested or len(requested) > MAX_RUN_CASES:
        raise InvalidRequest(f"Select between one and {MAX_RUN_CASES} evaluation cases.")
    if len(set(requested)) != len(requested):
        raise InvalidRequest("Each evaluation case can be selected once.")
    known = {case.id: case for case in catalogue}
    if any(case_id not in known for case_id in requested):
        raise InvalidRequest("An unknown evaluation case was selected.")
    wanted = set(requested)
    return tuple(case for case in catalogue if case.id in wanted)


def checked_call_cap(value: int) -> int:
    if type(value) is not int or not 1 <= value <= MAX_RUN_CALLS:
        raise InvalidRequest(f"The call cap must be a whole number from 1 to {MAX_RUN_CALLS}.")
    return value
