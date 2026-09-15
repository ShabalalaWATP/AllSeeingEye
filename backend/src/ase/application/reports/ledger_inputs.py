"""User-authored ledger fields. Scope, issue time and reviewer identity are server-owned."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ase.domain.doctrine import Probability
from ase.domain.forecast_ledger import (
    ConfidenceDimensions,
    ForecastState,
    ResolutionCriterion,
    ThresholdDirection,
)


@dataclass(frozen=True, slots=True)
class CitationKey:
    evidence_label: str
    excerpt_sha256: str


@dataclass(frozen=True, slots=True)
class ForecastCreate:
    claim_id: UUID
    claim_revision_id: UUID
    horizon_end: datetime
    review_at: datetime
    criterion: ResolutionCriterion
    likelihood: Probability
    confidence: ConfidenceDimensions
    supporting: tuple[CitationKey, ...]
    contrary: tuple[CitationKey, ...]


@dataclass(frozen=True, slots=True)
class IndicatorCreate:
    claim_id: UUID
    claim_revision_id: UUID
    condition: str
    metric_id: str
    unit: str
    source_id: str
    source_capability: str
    expected_update_hours: int
    source_citation: CitationKey
    threshold: Decimal | None = None
    direction: ThresholdDirection | None = None


@dataclass(frozen=True, slots=True)
class ForecastReview:
    previous_decision_id: UUID | None
    state: ForecastState
    reason: str
    evidence: tuple[CitationKey, ...]
    corrects_decision_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class MissingReading:
    observed_at: datetime
    missing_reason: str
    corrects_reading_id: UUID | None = None
