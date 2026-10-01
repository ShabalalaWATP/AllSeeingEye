"""Administrator research-quality scorecard: denominators and counts, never a percentage."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class QualityFindingOut(_Out):
    key: str
    rule: str
    severity: str
    versions: int
    occurrences: int


class QualityReceiptsOut(_Out):
    versions_with_receipts: int
    versions_without_receipts: int
    attempts: int
    completed: int
    empty: int
    unavailable: int
    other_unsuccessful: int
    versions_with_empty_or_unavailable: int


class QualityUsageOut(_Out):
    versions_with_usage: int
    versions_without_usage: int
    prompt_tokens: int
    completion_tokens: int
    prompt_tokens_per_version: int | None
    completion_tokens_per_version: int | None


class QualityVersionGroupOut(_Out):
    key: str
    label: str
    versions: int
    ready: int
    needs_review: int
    failed: int
    findings: list[QualityFindingOut]
    receipts: QualityReceiptsOut
    usage: QualityUsageOut


class QualityFailureCodeOut(_Out):
    code: str
    jobs: int


class QualityJobGroupOut(_Out):
    key: str
    label: str
    jobs: int
    queued: int
    running: int
    paused: int
    completed: int
    needs_review: int
    failed: int
    failed_without_version: int
    failed_with_version: int
    failure_codes: list[QualityFailureCodeOut]


class QualityVersionPopulationOut(_Out):
    bound: int
    in_window: int
    counted: int
    bound_reached: bool
    overall: QualityVersionGroupOut
    by_template: list[QualityVersionGroupOut]
    by_depth: list[QualityVersionGroupOut]
    by_connection: list[QualityVersionGroupOut]


class QualityJobPopulationOut(_Out):
    bound: int
    in_window: int
    counted: int
    bound_reached: bool
    overall: QualityJobGroupOut
    by_template: list[QualityJobGroupOut]
    by_depth: list[QualityJobGroupOut]
    by_model: list[QualityJobGroupOut]


class QualityCitationChecksOut(_Out):
    available: bool
    note: str
    bound: int
    in_window: int
    counted: int
    bound_reached: bool
    current_verdicts: int
    superseded_verdicts: int
    citations_with_verdicts: int
    supports: int
    partly_supports: int
    does_not_support: int
    cannot_tell: int


class ResearchQualityOut(_Out):
    generated_at: datetime
    window_days: int
    since: datetime
    versions: QualityVersionPopulationOut
    jobs: QualityJobPopulationOut
    citation_checks: QualityCitationChecksOut
