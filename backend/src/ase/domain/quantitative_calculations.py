"""Allowlisted exact calculations over retained quantitative observations.

Results are rational values. Rendering may round them, but the formula receipt
keeps their exact numerator/denominator and every input evidence reference.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from itertools import pairwise

from ase.domain.quantitative_observations import (
    MeasureKind,
    ObservationPeriod,
    QuantitativeObservation,
    QuantitativeSeries,
)

FORMULA_VERSION = 1


class Formula(StrEnum):
    ABSOLUTE_CHANGE = "absolute_change"
    PERCENTAGE_CHANGE = "percentage_change"
    INDEX_BASE_100 = "index_base_100"
    ROLLING_SUM = "rolling_sum"
    ROLLING_MEAN = "rolling_mean"
    RATE = "rate"
    ALIGNED_ABSOLUTE = "aligned_absolute"
    ALIGNED_PERCENTAGE = "aligned_percentage"


class RollingMethod(StrEnum):
    SUM = "sum"
    MEAN = "mean"


class AlignedMethod(StrEnum):
    ABSOLUTE = "absolute"
    PERCENTAGE = "percentage"


_EXPRESSIONS = {
    Formula.ABSOLUTE_CHANGE: "later - earlier",
    Formula.PERCENTAGE_CHANGE: "(later - earlier) / earlier * 100",
    Formula.INDEX_BASE_100: "observation / base * 100",
    Formula.ROLLING_SUM: "sum(complete contiguous window)",
    Formula.ROLLING_MEAN: "sum(complete contiguous window) / window_length",
    Formula.RATE: "numerator / denominator * scale",
    Formula.ALIGNED_ABSOLUTE: "right - left, same period",
    Formula.ALIGNED_PERCENTAGE: "(right - left) / left * 100, same period",
}


@dataclass(frozen=True, slots=True)
class FormulaInput:
    observation_id: str
    series_id: str
    measure_id: str
    entity_id: str
    measure_kind: MeasureKind
    source_id: str
    evidence_id: str
    reference: str
    period: ObservationPeriod
    exact_value: Decimal
    unit: str
    currency: str | None
    adjustment: str
    vintage: str
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class FormulaReceipt:
    formula: Formula
    version: int
    expression: str
    inputs: tuple[FormulaInput, ...]
    coverage: tuple[ObservationPeriod, ...]
    exact_numerator: int
    exact_denominator: int
    output_unit: str
    output_currency: str | None
    scale: int | None = None
    window_length: int | None = None


@dataclass(frozen=True, slots=True)
class QuantitativeResult:
    period: ObservationPeriod
    value: Fraction
    unit: str
    currency: str | None
    receipt: FormulaReceipt


def _value(item: QuantitativeObservation) -> Fraction:
    if item.value is None:
        raise ValueError(f"Observation {item.id} is missing; no value was interpolated")
    return Fraction(item.value)


def _compatible(
    left: QuantitativeObservation,
    right: QuantitativeObservation,
    *,
    same_entity: bool,
) -> None:
    if left.comparability_key != right.comparability_key or left.source_id != right.source_id:
        raise ValueError(
            "Observations differ in measure, unit, currency, frequency, "
            "adjustment, vintage, kind or source"
        )
    if same_entity and left.entity_id != right.entity_id:
        raise ValueError("Observations refer to different entities")


def _result(
    formula: Formula,
    value: Fraction,
    inputs: tuple[QuantitativeObservation, ...],
    *,
    period: ObservationPeriod,
    unit: str,
    currency: str | None,
    scale: int | None = None,
    window_length: int | None = None,
) -> QuantitativeResult:
    refs = tuple(
        FormulaInput(
            observation_id=item.id,
            series_id=item.series_id,
            measure_id=item.measure_id,
            entity_id=item.entity_id,
            measure_kind=item.measure_kind,
            source_id=item.source_id,
            evidence_id=item.evidence_id,
            reference=item.reference,
            period=item.period,
            exact_value=item.value,
            unit=item.unit,
            currency=item.currency,
            adjustment=item.adjustment.value,
            vintage=item.vintage,
            published_at=item.published_at,
        )
        for item in inputs
        if item.value is not None
    )
    if len(refs) != len(inputs):
        raise ValueError("A formula receipt cannot omit a missing source value")
    receipt = FormulaReceipt(
        formula=formula,
        version=FORMULA_VERSION,
        expression=_EXPRESSIONS[formula],
        inputs=refs,
        coverage=tuple(dict.fromkeys(item.period for item in inputs)),
        exact_numerator=value.numerator,
        exact_denominator=value.denominator,
        output_unit=unit,
        output_currency=currency,
        scale=scale,
        window_length=window_length,
    )
    return QuantitativeResult(period, value, unit, currency, receipt)


def absolute_change(
    earlier: QuantitativeObservation, later: QuantitativeObservation
) -> QuantitativeResult:
    _compatible(earlier, later, same_entity=True)
    if earlier.series_id != later.series_id or earlier.period.start >= later.period.start:
        raise ValueError("Change needs two ordered observations from one series")
    value = _value(later) - _value(earlier)
    return _result(
        Formula.ABSOLUTE_CHANGE,
        value,
        (earlier, later),
        period=later.period,
        unit=later.unit,
        currency=later.currency,
    )


def percentage_change(
    earlier: QuantitativeObservation, later: QuantitativeObservation
) -> QuantitativeResult:
    _compatible(earlier, later, same_entity=True)
    if earlier.series_id != later.series_id or earlier.period.start >= later.period.start:
        raise ValueError("Change needs two ordered observations from one series")
    base = _value(earlier)
    if not base:
        raise ValueError("Percentage change has a zero denominator")
    value = (_value(later) - base) / base * 100
    return _result(
        Formula.PERCENTAGE_CHANGE,
        value,
        (earlier, later),
        period=later.period,
        unit="percent",
        currency=None,
    )


def indexed_series(
    series: QuantitativeSeries, base_period: ObservationPeriod
) -> tuple[QuantitativeResult, ...]:
    if not isinstance(series, QuantitativeSeries) or not isinstance(base_period, ObservationPeriod):
        raise ValueError("Indexing needs a typed series and base period")
    base = next((item for item in series.observations if item.period == base_period), None)
    if base is None:
        raise ValueError("The base period is absent; it cannot be interpolated")
    base_value = _value(base)
    if not base_value:
        raise ValueError("Index base has a zero denominator")
    return tuple(
        _result(
            Formula.INDEX_BASE_100,
            _value(item) / base_value * 100,
            (base, item),
            period=item.period,
            unit="index (base=100)",
            currency=None,
        )
        for item in series.observations
    )


def rolling_summary(
    series: QuantitativeSeries, *, window: int, method: RollingMethod
) -> tuple[QuantitativeResult, ...]:
    if not isinstance(series, QuantitativeSeries) or not isinstance(method, RollingMethod):
        raise ValueError("Rolling summary needs a typed series and allowlisted method")
    if type(window) is not int or not 2 <= window <= 24 or len(series.observations) < window:
        raise ValueError("Rolling summary needs a supported window and enough observations")
    if method is RollingMethod.SUM and series.observations[0].measure_kind is not MeasureKind.FLOW:
        raise ValueError("Only additive flows may be summed across periods")
    results = []
    for end in range(window, len(series.observations) + 1):
        items = series.observations[end - window : end]
        if any(left.period.end != right.period.start for left, right in pairwise(items)):
            raise ValueError("Rolling summary cannot interpolate a missing period")
        total = sum((_value(item) for item in items), Fraction())
        value = total if method is RollingMethod.SUM else total / window
        results.append(
            _result(
                Formula.ROLLING_SUM if method is RollingMethod.SUM else Formula.ROLLING_MEAN,
                value,
                items,
                period=items[-1].period,
                unit=items[-1].unit,
                currency=items[-1].currency,
                window_length=window,
            )
        )
    return tuple(results)


def rate(
    numerator: QuantitativeObservation,
    denominator: QuantitativeObservation,
    *,
    scale: int = 1,
) -> QuantitativeResult:
    if type(scale) is not int or scale not in (1, 100, 1_000, 100_000):
        raise ValueError("Rate scale is not allowlisted")
    if (
        numerator.period != denominator.period
        or numerator.entity_id != denominator.entity_id
        or numerator.adjustment != denominator.adjustment
        or numerator.vintage != denominator.vintage
    ):
        raise ValueError("Rate inputs need the same entity, period, adjustment and vintage")
    if denominator.currency is not None and numerator.currency != denominator.currency:
        raise ValueError("Rate inputs cannot mix currencies")
    divisor = _value(denominator)
    if divisor <= 0:
        raise ValueError("Rate needs a positive denominator")
    value = _value(numerator) / divisor * scale
    unit = (
        f"{numerator.unit} per {scale} {denominator.unit}"
        if scale != 1
        else (f"{numerator.unit} per {denominator.unit}")
    )
    return _result(
        Formula.RATE,
        value,
        (numerator, denominator),
        period=numerator.period,
        unit=unit,
        currency=numerator.currency if denominator.currency is None else None,
        scale=scale,
    )


def aligned_period_comparison(
    left: QuantitativeSeries,
    right: QuantitativeSeries,
    *,
    method: AlignedMethod,
) -> tuple[QuantitativeResult, ...]:
    if not isinstance(left, QuantitativeSeries) or not isinstance(right, QuantitativeSeries):
        raise ValueError("Aligned comparison needs two typed series")
    if not isinstance(method, AlignedMethod) or len(left.observations) != len(right.observations):
        raise ValueError("Aligned comparison needs an allowlisted method and equal sample lengths")
    results = []
    for before, after in zip(left.observations, right.observations, strict=True):
        _compatible(before, after, same_entity=False)
        if before.period != after.period:
            raise ValueError("Comparison periods must align exactly; no interpolation is allowed")
        baseline = _value(before)
        difference = _value(after) - baseline
        if method is AlignedMethod.PERCENTAGE and not baseline:
            raise ValueError("Aligned percentage comparison has a zero denominator")
        value = difference if method is AlignedMethod.ABSOLUTE else difference / baseline * 100
        results.append(
            _result(
                Formula.ALIGNED_ABSOLUTE
                if method is AlignedMethod.ABSOLUTE
                else Formula.ALIGNED_PERCENTAGE,
                value,
                (before, after),
                period=after.period,
                unit=after.unit if method is AlignedMethod.ABSOLUTE else "percent",
                currency=after.currency if method is AlignedMethod.ABSOLUTE else None,
            )
        )
    return tuple(results)
