"""Append-only forecast versions and auditable resolution decisions.

This is a domain boundary, not a prediction service. Only a trusted caller may
attest the coverage and provenance of threshold observations or reviewer identity.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from ase.domain.doctrine import Confidence, Probability

FORECAST_POLICY_VERSION = "ase-forecast-ledger-v1"


def _text(value: str, name: str, limit: int = 200) -> None:
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be a non-empty bounded string")


def _time(value: datetime, name: str) -> None:
    if type(value) is not datetime or value.utcoffset() is None:
        raise ValueError(f"{name} needs a timezone")


def _decimal(value: object) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError("Threshold values must be finite Decimals")
    parts = value.as_tuple()
    if len(parts.digits) > 40 or not isinstance(parts.exponent, int) or abs(parts.exponent) > 24:
        raise ValueError("Threshold value exceeds supported precision")


class ThresholdDirection(StrEnum):
    AT_LEAST = "at_least"
    AT_MOST = "at_most"


class WindowAggregate(StrEnum):
    MAXIMUM = "maximum"
    MINIMUM = "minimum"


class ForecastState(StrEnum):
    OPEN = "open"
    DUE = "due"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"
    UNRESOLVED = "unresolved"


class DecisionMethod(StrEnum):
    REVIEWER = "reviewer"
    THRESHOLD = "verified_threshold"
    CLOCK = "clock"


@dataclass(frozen=True, slots=True)
class PassageReference:
    report_version_id: str
    evidence_id: str
    passage_id: str

    def __post_init__(self) -> None:
        for name in ("report_version_id", "evidence_id", "passage_id"):
            _text(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class ConfidenceDimensions:
    source_quality: Confidence
    corroboration: Confidence
    coverage: Confidence
    limitation: str

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, Confidence)
            for value in (self.source_quality, self.corroboration, self.coverage)
        ):
            raise ValueError("Forecast confidence dimensions must be explicit")
        _text(self.limitation, "confidence limitation", 1000)


@dataclass(frozen=True, slots=True)
class ResolutionCriterion:
    """An observed extreme within the issue-to-horizon window, or human review."""

    description: str
    metric_id: str | None = None
    source_id: str | None = None
    unit: str | None = None
    threshold: Decimal | None = None
    direction: ThresholdDirection | None = None
    aggregate: WindowAggregate | None = None

    def __post_init__(self) -> None:
        _text(self.description, "resolution criterion", 1000)
        fields = (
            self.metric_id,
            self.source_id,
            self.unit,
            self.threshold,
            self.direction,
            self.aggregate,
        )
        if all(value is None for value in fields):
            return
        if any(value is None for value in fields):
            raise ValueError("A threshold criterion needs metric, source, unit, value and method")
        for name in ("metric_id", "source_id", "unit"):
            _text(getattr(self, name), name)
        _decimal(self.threshold)
        if not isinstance(self.direction, ThresholdDirection) or not isinstance(
            self.aggregate, WindowAggregate
        ):
            raise ValueError("Unsupported threshold comparison")
        if (self.direction, self.aggregate) not in {
            (ThresholdDirection.AT_LEAST, WindowAggregate.MAXIMUM),
            (ThresholdDirection.AT_MOST, WindowAggregate.MINIMUM),
        }:
            raise ValueError("Threshold direction must match the window extreme")

    @property
    def is_threshold(self) -> bool:
        return self.threshold is not None


@dataclass(frozen=True, slots=True)
class ForecastVersion:
    forecast_id: str
    version_id: str
    version: int
    claim_id: str
    claim_version_id: str
    report_version_id: str
    issued_at: datetime
    horizon_end: datetime
    review_at: datetime
    criterion: ResolutionCriterion
    likelihood: Probability
    confidence: ConfidenceDimensions
    supporting: tuple[PassageReference, ...]
    contrary: tuple[PassageReference, ...]
    supersedes_version_id: str | None = None
    policy_version: str = FORECAST_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in (
            "forecast_id",
            "version_id",
            "claim_id",
            "claim_version_id",
            "report_version_id",
        ):
            _text(getattr(self, name), name)
        for name in ("issued_at", "horizon_end", "review_at"):
            _time(getattr(self, name), name)
        if not self.issued_at < self.horizon_end or not self.issued_at <= self.review_at:
            raise ValueError("Forecast horizon and review date must follow issue time")
        if type(self.version) is not int or self.version < 1 or self.version > 64:
            raise ValueError("Forecast version is outside supported range")
        if (
            not isinstance(self.criterion, ResolutionCriterion)
            or not isinstance(self.likelihood, Probability)
            or not isinstance(self.confidence, ConfidenceDimensions)
        ):
            raise ValueError("Forecast criterion, PHIA band and confidence are required")
        for refs in (self.supporting, self.contrary):
            if (
                type(refs) is not tuple
                or len(refs) > 64
                or any(not isinstance(ref, PassageReference) for ref in refs)
            ):
                raise ValueError("Forecast evidence must be bounded frozen passages")
        if (
            not self.supporting
            or len(set(self.supporting)) != len(self.supporting)
            or len(set(self.contrary)) != len(self.contrary)
            or set(self.supporting) & set(self.contrary)
        ):
            raise ValueError("Forecast needs support distinct from contrary evidence")
        if self.supersedes_version_id is not None:
            _text(self.supersedes_version_id, "superseded version")
        if self.policy_version != FORECAST_POLICY_VERSION:
            raise ValueError("Unsupported forecast ledger policy")


@dataclass(frozen=True, slots=True)
class ThresholdObservation:
    metric_id: str
    source_id: str
    unit: str
    aggregate: WindowAggregate
    value: Decimal | None
    window_start: datetime
    window_end: datetime
    coverage_verified: bool
    verification_reference: str | None
    passage: PassageReference | None

    def __post_init__(self) -> None:
        for name in ("metric_id", "source_id", "unit"):
            _text(getattr(self, name), name)
        _time(self.window_start, "window start")
        _time(self.window_end, "window end")
        if self.window_start > self.window_end or not isinstance(self.aggregate, WindowAggregate):
            raise ValueError("Invalid threshold observation window")
        if type(self.coverage_verified) is not bool:
            raise ValueError("Coverage verification must be explicit")
        if self.value is not None:
            _decimal(self.value)
            if self.passage is None or self.verification_reference is None:
                raise ValueError("Observed value needs a passage and verification receipt")
            _text(self.verification_reference, "verification reference")
        if self.coverage_verified:
            if self.value is None:
                raise ValueError("Full-window coverage needs an observed extreme")
        elif self.value is None and self.verification_reference is not None:
            raise ValueError("Missing observations cannot retain a verification receipt")


def evaluate_threshold(
    forecast: ForecastVersion, observation: ThresholdObservation, decided_at: datetime
) -> bool | None:
    """True for a witnessed crossing; false only for verified full-window absence."""

    _time(decided_at, "decision time")
    criterion = forecast.criterion
    if not criterion.is_threshold or observation.value is None or observation.passage is None:
        return None
    if (
        observation.metric_id != criterion.metric_id
        or observation.source_id != criterion.source_id
        or observation.unit != criterion.unit
        or observation.aggregate is not criterion.aggregate
        or observation.window_start < forecast.issued_at
        or observation.window_end > forecast.horizon_end
        or decided_at < observation.window_end
    ):
        return None
    threshold = criterion.threshold
    if threshold is None:
        return None
    matches = (
        observation.value >= threshold
        if criterion.direction is ThresholdDirection.AT_LEAST
        else observation.value <= threshold
    )
    if matches:
        return True
    if (
        observation.coverage_verified
        and observation.window_start == forecast.issued_at
        and observation.window_end == forecast.horizon_end
        and decided_at >= forecast.horizon_end
    ):
        return False
    return None
