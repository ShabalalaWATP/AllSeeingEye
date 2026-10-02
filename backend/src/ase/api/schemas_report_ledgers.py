"""Bounded report-ledger inputs; server owns identifiers, clocks and reviewer identity."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from ase.application.reports.ledger_inputs import (
    CitationKey,
    ForecastCreate,
    ForecastReview,
    ForecastSupersession,
    IndicatorCreate,
    MissingReading,
    OutcomeEvidence,
)
from ase.domain.doctrine import Confidence, Probability
from ase.domain.forecast_ledger import (
    ConfidenceDimensions,
    ForecastState,
    ResolutionCriterion,
    ThresholdDirection,
    WindowAggregate,
)
from ase.domain.forecast_views import ForecastWatch
from ase.domain.report_ledgers import ReportLedger

Short = Annotated[str, Field(min_length=1, max_length=200)]
Reason = Annotated[str, Field(min_length=1, max_length=2000)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class CitationKeyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_label: Annotated[str, Field(min_length=1, max_length=32)]
    excerpt_sha256: Sha256

    def to_domain(self) -> CitationKey:
        return CitationKey(self.evidence_label, self.excerpt_sha256)


class CriterionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: Annotated[str, Field(min_length=1, max_length=1000)]
    metric_id: Short | None = None
    source_id: Short | None = None
    unit: Short | None = None
    threshold: Decimal | None = None
    direction: ThresholdDirection | None = None
    aggregate: WindowAggregate | None = None

    def to_domain(self) -> ResolutionCriterion:
        return ResolutionCriterion(
            self.description,
            self.metric_id,
            self.source_id,
            self.unit,
            self.threshold,
            self.direction,
            self.aggregate,
        )


class ConfidenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_quality: Confidence
    corroboration: Confidence
    coverage: Confidence
    limitation: Annotated[str, Field(min_length=1, max_length=1000)]

    def to_domain(self) -> ConfidenceDimensions:
        return ConfidenceDimensions(
            self.source_quality, self.corroboration, self.coverage, self.limitation
        )


class ForecastCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: UUID
    claim_revision_id: UUID
    horizon_end: datetime
    review_at: datetime
    criterion: CriterionIn
    likelihood: Probability
    confidence: ConfidenceIn
    supporting: Annotated[tuple[CitationKeyIn, ...], Field(min_length=1, max_length=20)]
    contrary: Annotated[tuple[CitationKeyIn, ...], Field(max_length=20)] = ()

    def to_domain(self) -> ForecastCreate:
        return ForecastCreate(
            self.claim_id,
            self.claim_revision_id,
            self.horizon_end,
            self.review_at,
            self.criterion.to_domain(),
            self.likelihood,
            self.confidence.to_domain(),
            tuple(row.to_domain() for row in self.supporting),
            tuple(row.to_domain() for row in self.contrary),
        )


class IndicatorCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: UUID
    claim_revision_id: UUID
    condition: Annotated[str, Field(min_length=1, max_length=500)]
    metric_id: Short
    unit: Short
    source_id: Short
    source_capability: Annotated[str, Field(min_length=1, max_length=500)]
    expected_update_hours: Annotated[StrictInt, Field(ge=1, le=8784)]
    source_citation: CitationKeyIn
    threshold: Decimal | None = None
    direction: ThresholdDirection | None = None

    def to_domain(self) -> IndicatorCreate:
        return IndicatorCreate(
            self.claim_id,
            self.claim_revision_id,
            self.condition,
            self.metric_id,
            self.unit,
            self.source_id,
            self.source_capability,
            self.expected_update_hours,
            self.source_citation.to_domain(),
            self.threshold,
            self.direction,
        )


class OutcomeEvidenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_id: UUID
    version: int = Field(ge=1, le=2_147_483_647)
    claim_id: UUID
    claim_revision_id: UUID
    citation: CitationKeyIn

    def to_domain(self) -> OutcomeEvidence:
        return OutcomeEvidence(
            self.report_id,
            self.version,
            self.claim_id,
            self.claim_revision_id,
            self.citation.to_domain(),
        )


class ForecastSupersessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version_id: UUID
    previous_decision_id: UUID | None = None
    reason: Reason
    replacement: ForecastCreateIn

    def to_domain(self) -> ForecastSupersession:
        return ForecastSupersession(
            self.expected_version_id,
            self.previous_decision_id,
            self.reason,
            self.replacement.to_domain(),
        )


class ForecastReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version_id: UUID | None = None
    previous_decision_id: UUID | None = None
    state: Literal[ForecastState.UNRESOLVED, ForecastState.RESOLVED]
    outcome: StrictBool | None = None
    outcome_evidence: Annotated[tuple[OutcomeEvidenceIn, ...], Field(max_length=20)] = ()
    reason: Reason
    evidence: Annotated[tuple[CitationKeyIn, ...], Field(max_length=20)] = ()
    corrects_decision_id: UUID | None = None

    def to_domain(self) -> ForecastReview:
        return ForecastReview(
            self.previous_decision_id,
            self.state,
            self.reason,
            tuple(row.to_domain() for row in self.evidence),
            self.corrects_decision_id,
            self.outcome,
            tuple(row.to_domain() for row in self.outcome_evidence),
            self.expected_version_id,
        )


class MissingReadingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observed_at: datetime
    missing_reason: Annotated[str, Field(min_length=1, max_length=500)]
    corrects_reading_id: UUID | None = None

    def to_domain(self) -> MissingReading:
        return MissingReading(self.observed_at, self.missing_reason, self.corrects_reading_id)


class ReportLedgerPageOut(BaseModel):
    items: tuple[ReportLedger, ...]
    total: int
    limit: int
    offset: int


class ForecastWatchPageOut(BaseModel):
    items: tuple[ForecastWatch, ...]
    total: int
    limit: int
    offset: int


class ForecastExportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ledger_ids: tuple[UUID, ...] = Field(min_length=1, max_length=20)
