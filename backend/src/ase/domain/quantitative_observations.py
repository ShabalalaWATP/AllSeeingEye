"""Exact, source-linked observations admitted to deterministic calculations.

Capture adapters must construct these from source values before float conversion.
No unit, vintage or missing value is inferred by this domain boundary.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise


class Frequency(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class SeasonalAdjustment(StrEnum):
    UNADJUSTED = "unadjusted"
    SEASONALLY_ADJUSTED = "seasonally_adjusted"
    TREND = "trend"
    UNKNOWN = "unknown"


class MeasureKind(StrEnum):
    FLOW = "flow"
    STOCK = "stock"
    INDEX = "index"
    RATE = "rate"


def _next_period(start: date, frequency: Frequency) -> date:
    if frequency is Frequency.DAILY:
        return date.fromordinal(start.toordinal() + 1)
    months = {
        Frequency.MONTHLY: 1,
        Frequency.QUARTERLY: 3,
        Frequency.ANNUAL: 12,
    }[frequency]
    month_index = start.year * 12 + start.month - 1 + months
    return date(month_index // 12, month_index % 12 + 1, 1)


@dataclass(frozen=True, slots=True)
class ObservationPeriod:
    """A complete calendar period, represented by its start and frequency."""

    start: date
    frequency: Frequency

    def __post_init__(self) -> None:
        if type(self.start) is not date or not isinstance(self.frequency, Frequency):
            raise ValueError("A calendar date and supported frequency are required")
        if self.frequency is not Frequency.DAILY and self.start.day != 1:
            raise ValueError("Monthly or longer periods must start on day one")
        if self.frequency is Frequency.QUARTERLY and self.start.month not in (1, 4, 7, 10):
            raise ValueError("Quarterly periods must start at a quarter boundary")
        if self.frequency is Frequency.ANNUAL and self.start.month != 1:
            raise ValueError("Annual periods must start in January")
        if self.start.year < 1900 or self.start.year > 2100:
            raise ValueError("Observation period is outside the supported date range")

    @property
    def end(self) -> date:
        return _next_period(self.start, self.frequency)


def _label(value: str, name: str, limit: int = 160) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be a non-empty bounded string")


def _bounded_decimal(value: object) -> bool:
    if type(value) is not Decimal or not value.is_finite():
        return False
    exponent = value.as_tuple().exponent
    return isinstance(exponent, int) and len(value.as_tuple().digits) <= 40 and abs(exponent) <= 24


@dataclass(frozen=True, slots=True)
class QuantitativeObservation:
    """A single source value, including explicit missingness and evidence identity."""

    id: str
    series_id: str
    measure_id: str
    entity_id: str
    period: ObservationPeriod
    value: Decimal | None
    unit: str
    currency: str | None
    adjustment: SeasonalAdjustment
    vintage: str
    measure_kind: MeasureKind
    source_id: str
    evidence_id: str
    reference: str
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        for name in (
            "id",
            "series_id",
            "measure_id",
            "entity_id",
            "unit",
            "vintage",
            "source_id",
            "evidence_id",
        ):
            _label(getattr(self, name), name)
        _label(self.reference, "reference", 2000)
        if not isinstance(self.period, ObservationPeriod):
            raise ValueError("A typed observation period is required")
        if not isinstance(self.adjustment, SeasonalAdjustment):
            raise ValueError("Seasonal adjustment must be explicit")
        if not isinstance(self.measure_kind, MeasureKind):
            raise ValueError("Measure kind must be explicit")
        if self.currency is not None and (
            type(self.currency) is not str
            or len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isupper()
            or not self.currency.isalpha()
        ):
            raise ValueError("Currency must be an ISO-style three-letter code")
        value = self.value
        if value is not None and not _bounded_decimal(value):
            raise ValueError("Observation value must be a finite bounded Decimal or missing")
        if self.published_at is not None and (
            not isinstance(self.published_at, datetime) or self.published_at.utcoffset() is None
        ):
            raise ValueError("Source publication time must include a timezone")

    @property
    def comparability_key(
        self,
    ) -> tuple[str, str, str | None, Frequency, SeasonalAdjustment, str, MeasureKind]:
        return (
            self.measure_id,
            self.unit,
            self.currency,
            self.period.frequency,
            self.adjustment,
            self.vintage,
            self.measure_kind,
        )


@dataclass(frozen=True, slots=True)
class QuantitativeSeries:
    observations: tuple[QuantitativeObservation, ...]

    def __post_init__(self) -> None:
        items = self.observations
        if type(items) is not tuple or not 1 <= len(items) <= 120:
            raise ValueError("A series needs one to 120 immutable observations")
        if any(not isinstance(item, QuantitativeObservation) for item in items):
            raise ValueError("A series needs typed observations")
        first = items[0]
        if len({item.id for item in items}) != len(items):
            raise ValueError("Series observation identities must be unique")
        for previous, current in pairwise(items):
            if (
                current.series_id != first.series_id
                or current.entity_id != first.entity_id
                or current.comparability_key != first.comparability_key
                or current.source_id != first.source_id
            ):
                raise ValueError("Series metadata must remain comparable across periods")
            if current.period.start <= previous.period.start:
                raise ValueError("Series periods must be strictly increasing and unique")
