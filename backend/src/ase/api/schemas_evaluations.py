"""Evaluation run contracts. Outputs carry no endpoint address, key or connection hash."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.application.admin.evaluations import EvaluationStart
from ase.domain.evaluations import (
    CALLS_PER_CASE,
    ESTIMATE_NOTICE,
    MAX_CASE_ID_LENGTH,
    MAX_RUN_CALLS,
    MAX_RUN_CASES,
    RESULT_NOTICE,
    EvaluationCaseInfo,
    EvaluationCaseSummary,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationStopReason,
)

CaseId = Annotated[str, Field(min_length=1, max_length=MAX_CASE_ID_LENGTH)]


class EvaluationCaseOut(BaseModel):
    id: str
    casebook: Literal["core", "regional"]
    title: str
    fingerprint: str

    @classmethod
    def from_case(cls, case: EvaluationCaseInfo) -> Self:
        casebook: Literal["core", "regional"] = "core" if case.casebook == "core" else "regional"
        return cls(id=case.id, casebook=casebook, title=case.title, fingerprint=case.fingerprint)


class EvaluationCatalogueOut(BaseModel):
    cases: list[EvaluationCaseOut]
    calls_per_case: int = CALLS_PER_CASE
    max_calls: int = MAX_RUN_CALLS
    max_cases: int = MAX_RUN_CASES
    estimate_notice: str = ESTIMATE_NOTICE
    result_notice: str = RESULT_NOTICE


class EvaluationStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: UUID
    case_ids: list[CaseId] = Field(min_length=1, max_length=MAX_RUN_CASES)
    max_calls: int = Field(ge=1, le=MAX_RUN_CALLS)

    def to_input(self) -> EvaluationStart:
        return EvaluationStart(self.profile_id, list(self.case_ids), self.max_calls)


class EvaluationCaseResultOut(BaseModel):
    case_id: str
    fingerprint: str
    report_status: str
    model_calls: int
    prompt_tokens: int | None
    completion_tokens: int | None
    checks: dict[str, int | float | bool | None] = Field(
        description="Deterministic structural checks only; never accuracy."
    )

    @classmethod
    def from_summary(cls, summary: EvaluationCaseSummary) -> Self:
        return cls(
            case_id=summary.case_id,
            fingerprint=summary.fingerprint,
            report_status=summary.report_status,
            model_calls=summary.model_calls,
            prompt_tokens=summary.prompt_tokens,
            completion_tokens=summary.completion_tokens,
            checks=dict(summary.checks),
        )


class EvaluationRunOut(BaseModel):
    id: UUID
    profile_id: UUID
    profile_name: str
    model: str
    status: EvaluationRunStatus
    stop_reason: EvaluationStopReason | None
    cancel_requested: bool
    case_ids: list[str]
    case_fingerprints: dict[str, str]
    max_calls: int
    estimated_calls: int
    calls_reserved: int
    calls_failed: int
    prompt_tokens: int | None
    completion_tokens: int | None
    results: list[EvaluationCaseResultOut]
    has_artefact: bool
    created_at: datetime
    finished_at: datetime | None
    notice: str = RESULT_NOTICE

    @classmethod
    def from_run(cls, run: EvaluationRun) -> Self:
        return cls(
            id=run.id,
            profile_id=run.profile_id,
            profile_name=run.profile_name,
            model=run.model,
            status=run.status,
            stop_reason=run.stop_reason,
            cancel_requested=run.cancel_requested,
            case_ids=list(run.case_ids),
            case_fingerprints=dict(run.case_fingerprints),
            max_calls=run.max_calls,
            estimated_calls=run.estimate.calls,
            calls_reserved=run.calls_reserved,
            calls_failed=run.calls_failed,
            prompt_tokens=_total([item.prompt_tokens for item in run.results]),
            completion_tokens=_total([item.completion_tokens for item in run.results]),
            results=[EvaluationCaseResultOut.from_summary(item) for item in run.results],
            has_artefact=run.has_artefact,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )


class EvaluationRunsOut(BaseModel):
    items: list[EvaluationRunOut]


def _total(values: list[int | None]) -> int | None:
    known = [value for value in values if value is not None]
    return sum(known) if known else None
