"""Versioned indicator readings with explicit unknown and append-only corrections."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from ase.domain.forecast_ledger import (
    PassageReference,
    ThresholdDirection,
    _decimal,
    _text,
    _time,
)

INDICATOR_POLICY_VERSION = "ase-indicator-ledger-v1"


class IndicatorStatus(StrEnum):
    MET = "met"
    NOT_MET = "not_met"
    UNKNOWN = "unknown"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class IndicatorVersion:
    indicator_id: str
    version_id: str
    version: int
    condition: str
    metric_id: str
    unit: str
    source_id: str
    source_capability: str
    expected_update_hours: int
    issued_at: datetime
    threshold: Decimal | None = None
    direction: ThresholdDirection | None = None
    supersedes_version_id: str | None = None
    policy_version: str = INDICATOR_POLICY_VERSION
    source_reference: PassageReference | None = None

    def __post_init__(self) -> None:
        for name in ("indicator_id", "version_id", "metric_id", "unit", "source_id"):
            _text(getattr(self, name), name)
        _text(self.condition, "observable condition", 500)
        _text(self.source_capability, "source capability", 500)
        if self.source_reference is not None and not isinstance(
            self.source_reference, PassageReference
        ):
            raise ValueError("Indicator source reference must be a frozen passage")
        _time(self.issued_at, "indicator issue time")
        if type(self.version) is not int or not 1 <= self.version <= 64:
            raise ValueError("Indicator version is outside supported range")
        if (
            type(self.expected_update_hours) is not int
            or not 1 <= self.expected_update_hours <= 24 * 366
        ):
            raise ValueError("Expected update frequency must be one hour to one year")
        if (self.threshold is None) != (self.direction is None):
            raise ValueError("Threshold value and direction must be set together")
        if self.threshold is not None:
            _decimal(self.threshold)
            if not isinstance(self.direction, ThresholdDirection):
                raise ValueError("Unsupported indicator threshold direction")
        if self.supersedes_version_id is not None:
            _text(self.supersedes_version_id, "superseded indicator version")
        if self.policy_version != INDICATOR_POLICY_VERSION:
            raise ValueError("Unsupported indicator policy")


@dataclass(frozen=True, slots=True)
class IndicatorReading:
    id: str
    indicator_version_id: str
    observed_at: datetime
    recorded_at: datetime
    unit: str
    value: Decimal | None
    passage: PassageReference | None
    verification_reference: str | None
    missing_reason: str | None = None
    corrects_reading_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("id", "indicator_version_id", "unit"):
            _text(getattr(self, name), name)
        for name in ("observed_at", "recorded_at"):
            _time(getattr(self, name), name)
        if self.observed_at > self.recorded_at:
            raise ValueError("A reading cannot be captured before observation")
        if self.value is None:
            if self.passage is not None or self.verification_reference is not None:
                raise ValueError("Missing data cannot carry an observed value citation")
            if self.missing_reason is None:
                raise ValueError("Missing data needs an explicit reason")
            _text(self.missing_reason, "missing reason", 500)
        else:
            _decimal(self.value)
            if self.passage is None or self.verification_reference is None:
                raise ValueError("A value needs a frozen passage and verification receipt")
            _text(self.verification_reference, "verification reference")
            if self.missing_reason is not None:
                raise ValueError("An observed value cannot also be missing")
        if self.corrects_reading_id is not None:
            _text(self.corrects_reading_id, "corrected reading")


@dataclass(frozen=True, slots=True)
class IndicatorEvaluation:
    status: IndicatorStatus
    version_id: str
    reading_id: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class IndicatorLedger:
    versions: tuple[IndicatorVersion, ...]
    readings: tuple[IndicatorReading, ...] = ()

    def __post_init__(self) -> None:
        _validate_versions(self.versions)
        _validate_readings(self.versions, self.readings)

    def append(self, reading: IndicatorReading) -> "IndicatorLedger":
        return IndicatorLedger(self.versions, (*self.readings, reading))

    def supersede(self, new_version: IndicatorVersion) -> "IndicatorLedger":
        return IndicatorLedger((*self.versions, new_version), self.readings)

    def evaluate_at(self, when: datetime) -> IndicatorEvaluation:
        _time(when, "evaluation time")
        version = next((row for row in reversed(self.versions) if row.issued_at <= when), None)
        if version is None:
            raise ValueError("Indicator evaluation cannot predate its first version")
        visible = tuple(
            row
            for row in self.readings
            if row.indicator_version_id == version.version_id and row.recorded_at <= when
        )
        corrected = {row.corrects_reading_id for row in visible if row.corrects_reading_id}
        current = (row for row in visible if row.id not in corrected)
        latest = max(current, key=lambda row: (row.observed_at, row.recorded_at), default=None)
        if latest is None:
            return IndicatorEvaluation(
                IndicatorStatus.UNKNOWN,
                version.version_id,
                None,
                "No source observation is available",
            )
        if latest.value is None:
            return IndicatorEvaluation(
                IndicatorStatus.UNKNOWN, version.version_id, latest.id, "Source data is missing"
            )
        if when - latest.observed_at > timedelta(hours=version.expected_update_hours):
            return IndicatorEvaluation(
                IndicatorStatus.STALE, version.version_id, latest.id, "Source observation is stale"
            )
        if version.threshold is None:
            return IndicatorEvaluation(
                IndicatorStatus.UNKNOWN,
                version.version_id,
                latest.id,
                "No deterministic threshold defines this condition",
            )
        met = (
            latest.value >= version.threshold
            if version.direction is ThresholdDirection.AT_LEAST
            else latest.value <= version.threshold
        )
        return IndicatorEvaluation(
            IndicatorStatus.MET if met else IndicatorStatus.NOT_MET,
            version.version_id,
            latest.id,
            ("Observed value meets threshold" if met else "Observed value does not meet threshold"),
        )


def _validate_versions(rows: tuple[IndicatorVersion, ...]) -> None:
    if type(rows) is not tuple or not 1 <= len(rows) <= 64:
        raise ValueError("Indicator ledger needs one to 64 immutable versions")
    if any(not isinstance(row, IndicatorVersion) for row in rows):
        raise ValueError("Indicator versions must be typed")
    if len({row.version_id for row in rows}) != len(rows):
        raise ValueError("Indicator version IDs must be unique")
    for number, row in enumerate(rows, 1):
        previous = rows[number - 2] if number > 1 else None
        if row.version != number or row.indicator_id != rows[0].indicator_id:
            raise ValueError("Indicator versions must be consecutive for one condition")
        if row.supersedes_version_id != (previous.version_id if previous else None):
            raise ValueError("Indicator versions need consecutive supersession links")
        if previous is not None and row.issued_at <= previous.issued_at:
            raise ValueError("An indicator version must be issued later")


def _validate_readings(
    versions: tuple[IndicatorVersion, ...], readings: tuple[IndicatorReading, ...]
) -> None:
    if type(readings) is not tuple or len(readings) > 4096:
        raise ValueError("Indicator readings exceed the immutable cap")
    by_version = {row.version_id: row for row in versions}
    next_issued = {
        row.version_id: versions[index + 1].issued_at for index, row in enumerate(versions[:-1])
    }
    seen: dict[str, IndicatorReading] = {}
    corrected: set[str] = set()
    unique_times: set[tuple[str, datetime]] = set()
    last_recorded: datetime | None = None
    for reading in readings:
        if not isinstance(reading, IndicatorReading) or reading.id in seen:
            raise ValueError("Readings require typed unique IDs")
        version = by_version.get(reading.indicator_version_id)
        if version is None or reading.unit != version.unit:
            raise ValueError("Reading must match a known indicator version and unit")
        if reading.observed_at < version.issued_at:
            raise ValueError("A reading cannot predate its indicator version")
        if (
            reading.indicator_version_id in next_issued
            and reading.observed_at >= next_issued[reading.indicator_version_id]
        ):
            raise ValueError("A superseded indicator cannot acquire new-period observations")
        if last_recorded is not None and reading.recorded_at < last_recorded:
            raise ValueError("Reading ledger must be ordered by capture time")
        last_recorded = reading.recorded_at
        _validate_reading_link(reading, seen, corrected, unique_times)
        seen[reading.id] = reading


def _validate_reading_link(
    reading: IndicatorReading,
    seen: dict[str, IndicatorReading],
    corrected: set[str],
    unique_times: set[tuple[str, datetime]],
) -> None:
    key = (reading.indicator_version_id, reading.observed_at)
    prior_id = reading.corrects_reading_id
    if prior_id is None:
        if key in unique_times:
            raise ValueError("A repeated observation needs a correction link")
        unique_times.add(key)
        return
    prior = seen.get(prior_id)
    if (
        prior is None
        or prior_id in corrected
        or prior.indicator_version_id != reading.indicator_version_id
        or prior.observed_at != reading.observed_at
        or reading.recorded_at <= prior.recorded_at
    ):
        raise ValueError("Correction must link the latest reading at the same time")
    corrected.add(prior_id)
