"""Exact, source-grounded quantitative calculations and refusal cases."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from fractions import Fraction

import pytest

from ase.domain.quantitative_calculations import (
    FORMULA_VERSION,
    AlignedMethod,
    Formula,
    RollingMethod,
    absolute_change,
    aligned_period_comparison,
    indexed_series,
    percentage_change,
    rate,
    rolling_summary,
)
from ase.domain.quantitative_observations import (
    Frequency,
    MeasureKind,
    ObservationPeriod,
    QuantitativeObservation,
    QuantitativeSeries,
    SeasonalAdjustment,
)


def observed(
    month: int,
    value: str | None,
    *,
    year: int = 2025,
    entity: str = "GB",
    series: str = "gb-events",
    source: str = "official-series",
    measure: str = "events",
    unit: str = "events",
    kind: MeasureKind = MeasureKind.FLOW,
    currency: str | None = None,
) -> QuantitativeObservation:
    period = ObservationPeriod(date(year, month, 1), Frequency.MONTHLY)
    return QuantitativeObservation(
        id=f"{series}:{year}-{month:02d}",
        series_id=series,
        measure_id=measure,
        entity_id=entity,
        period=period,
        value=Decimal(value) if value is not None else None,
        unit=unit,
        currency=currency,
        adjustment=SeasonalAdjustment.UNADJUSTED,
        vintage="release-2026-01",
        measure_kind=kind,
        source_id=source,
        evidence_id=f"evidence:{series}:{year}-{month:02d}",
        reference=f"https://example.test/{series}/{year}-{month:02d}",
        published_at=datetime(2026, 1, 15, tzinfo=UTC),
    )


def test_absolute_and_percentage_change_keep_exact_inputs_and_formula_receipt() -> None:
    first, second = observed(1, "0.1"), observed(2, "0.3")

    absolute = absolute_change(first, second)
    percent = percentage_change(first, second)

    assert absolute.value == Fraction(1, 5)
    assert absolute.unit == "events"
    assert percent.value == 200
    assert percent.unit == "percent"
    assert percent.receipt.formula is Formula.PERCENTAGE_CHANGE
    assert percent.receipt.version == FORMULA_VERSION
    assert percent.receipt.expression == "(later - earlier) / earlier * 100"
    assert percent.receipt.exact_numerator == 200
    assert percent.receipt.exact_denominator == 1
    assert [item.exact_value for item in percent.receipt.inputs] == [Decimal("0.1"), Decimal("0.3")]
    assert [item.evidence_id for item in percent.receipt.inputs] == [
        first.evidence_id,
        second.evidence_id,
    ]
    assert percent.receipt.inputs[0].reference == first.reference
    assert percent.receipt.inputs[0].vintage == first.vintage
    assert percent.receipt.inputs[0].published_at == first.published_at
    assert percent.receipt.inputs[0].series_id == first.series_id
    assert percent.receipt.inputs[0].entity_id == first.entity_id
    assert percent.receipt.coverage == (first.period, second.period)


def test_percentage_change_keeps_exact_repeating_fraction() -> None:
    result = percentage_change(observed(1, "3"), observed(2, "4"))
    assert result.value == Fraction(100, 3)
    assert (result.receipt.exact_numerator, result.receipt.exact_denominator) == (100, 3)


def test_indexed_series_uses_only_present_nonzero_base() -> None:
    items = (observed(1, "20"), observed(2, "25"), observed(3, "30"))
    results = indexed_series(QuantitativeSeries(items), items[0].period)
    assert [result.value for result in results] == [100, 125, 150]
    assert all(result.receipt.formula is Formula.INDEX_BASE_100 for result in results)
    assert results[1].receipt.inputs[0].observation_id == items[0].id
    assert results[1].receipt.inputs[1].observation_id == items[1].id
    assert results[1].unit == "index (base=100)"
    with pytest.raises(ValueError, match="base period is absent"):
        indexed_series(
            QuantitativeSeries(items), ObservationPeriod(date(2024, 1, 1), Frequency.MONTHLY)
        )
    with pytest.raises(ValueError, match="zero denominator"):
        indexed_series(QuantitativeSeries((observed(1, "0"), items[1])), items[0].period)


def test_rolling_sum_and_mean_require_complete_contiguous_windows() -> None:
    items = (observed(1, "1"), observed(2, "2"), observed(3, "4"))
    series = QuantitativeSeries(items)
    sums = rolling_summary(series, window=2, method=RollingMethod.SUM)
    means = rolling_summary(series, window=2, method=RollingMethod.MEAN)
    assert [result.value for result in sums] == [3, 6]
    assert [result.value for result in means] == [Fraction(3, 2), 3]
    assert sums[1].receipt.coverage == (items[1].period, items[2].period)
    assert sums[1].receipt.window_length == 2
    assert sums[1].receipt.formula is Formula.ROLLING_SUM

    with pytest.raises(ValueError, match="interpolate a missing period"):
        rolling_summary(
            QuantitativeSeries((items[0], items[2])), window=2, method=RollingMethod.MEAN
        )
    with pytest.raises(ValueError, match="enough observations"):
        rolling_summary(series, window=4, method=RollingMethod.MEAN)
    with pytest.raises(ValueError, match="missing"):
        rolling_summary(
            QuantitativeSeries((items[0], observed(2, None))),
            window=2,
            method=RollingMethod.MEAN,
        )
    with pytest.raises(ValueError, match="Only additive flows"):
        rolling_summary(
            QuantitativeSeries(
                tuple(replace(item, measure_kind=MeasureKind.STOCK) for item in items)
            ),
            window=2,
            method=RollingMethod.SUM,
        )


def test_rate_has_explicit_denominator_scale_units_and_exact_fraction() -> None:
    numerator = observed(1, "1", measure="cases", unit="cases")
    denominator = observed(
        1, "3", series="population", measure="population", unit="people", kind=MeasureKind.STOCK
    )
    result = rate(numerator, denominator, scale=1_000)
    assert result.value == Fraction(1_000, 3)
    assert result.unit == "cases per 1000 people"
    assert result.receipt.scale == 1_000
    assert result.receipt.formula is Formula.RATE
    assert [item.evidence_id for item in result.receipt.inputs] == [
        numerator.evidence_id,
        denominator.evidence_id,
    ]
    with pytest.raises(ValueError, match="positive denominator"):
        rate(numerator, replace(denominator, value=Decimal(0)))
    with pytest.raises(ValueError, match="positive denominator"):
        rate(numerator, replace(denominator, value=Decimal(-3)))
    with pytest.raises(ValueError, match="allowlisted"):
        rate(numerator, denominator, scale=7)
    with pytest.raises(ValueError, match="same entity, period"):
        rate(
            numerator,
            replace(denominator, period=ObservationPeriod(date(2025, 2, 1), Frequency.MONTHLY)),
        )


def test_aligned_period_comparison_checks_exact_alignment_and_comparability() -> None:
    left = QuantitativeSeries((observed(1, "10"), observed(2, "20")))
    right = QuantitativeSeries(
        (
            observed(1, "15", entity="US", series="us-events"),
            observed(2, "30", entity="US", series="us-events"),
        )
    )
    absolute = aligned_period_comparison(left, right, method=AlignedMethod.ABSOLUTE)
    percentage = aligned_period_comparison(left, right, method=AlignedMethod.PERCENTAGE)
    assert [result.value for result in absolute] == [5, 10]
    assert [result.value for result in percentage] == [50, 50]
    assert percentage[0].receipt.formula is Formula.ALIGNED_PERCENTAGE
    assert percentage[0].receipt.coverage == (left.observations[0].period,)
    shifted = QuantitativeSeries(
        (
            replace(
                right.observations[0], period=ObservationPeriod(date(2025, 3, 1), Frequency.MONTHLY)
            ),
            replace(
                right.observations[1], period=ObservationPeriod(date(2025, 4, 1), Frequency.MONTHLY)
            ),
        )
    )
    with pytest.raises(ValueError, match="periods must align"):
        aligned_period_comparison(left, shifted, method=AlignedMethod.ABSOLUTE)
    with pytest.raises(ValueError, match="equal sample lengths"):
        aligned_period_comparison(
            left, QuantitativeSeries(right.observations[:1]), method=AlignedMethod.ABSOLUTE
        )


@pytest.mark.parametrize(
    ("changed", "message"),
    [
        ({"unit": "people"}, "unit"),
        ({"currency": "USD"}, "currency"),
        ({"adjustment": SeasonalAdjustment.SEASONALLY_ADJUSTED}, "adjustment"),
        ({"vintage": "release-2026-02"}, "vintage"),
        ({"source_id": "another-source"}, "source"),
        ({"period": ObservationPeriod(date(2025, 4, 1), Frequency.QUARTERLY)}, "frequency"),
        ({"entity_id": "US"}, "different entities"),
    ],
)
def test_change_rejects_incomparable_metadata(changed: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        absolute_change(observed(1, "1"), replace(observed(2, "2"), **changed))


def test_null_and_zero_are_never_silently_coerced() -> None:
    with pytest.raises(ValueError, match="missing"):
        absolute_change(observed(1, None), observed(2, "2"))
    with pytest.raises(ValueError, match="zero denominator"):
        percentage_change(observed(1, "0"), observed(2, "2"))
    with pytest.raises(ValueError, match="missing"):
        aligned_period_comparison(
            QuantitativeSeries((observed(1, None),)),
            QuantitativeSeries((observed(1, "2", entity="US", series="us-events"),)),
            method=AlignedMethod.ABSOLUTE,
        )


def test_typed_boundary_rejects_float_nonfinite_unsupported_method_and_invented_provenance() -> (
    None
):
    item = observed(1, "1")
    for invalid in (1.1, Decimal("NaN"), Decimal("Infinity"), Decimal("1e100")):
        with pytest.raises(ValueError, match="finite bounded Decimal"):
            replace(item, value=invalid)
    with pytest.raises(ValueError, match="evidence_id"):
        replace(item, evidence_id="")
    with pytest.raises(ValueError, match="allowlisted method"):
        rolling_summary(QuantitativeSeries((item, observed(2, "2"))), window=2, method="eval")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="allowlisted method"):
        aligned_period_comparison(
            QuantitativeSeries((item,)),
            QuantitativeSeries((item,)),
            method="eval",  # type: ignore[arg-type]
        )


def test_calendar_boundaries_and_duplicate_periods_are_rejected() -> None:
    assert ObservationPeriod(date(2024, 2, 1), Frequency.MONTHLY).end == date(2024, 3, 1)
    assert ObservationPeriod(date(2024, 1, 1), Frequency.ANNUAL).end == date(2025, 1, 1)
    with pytest.raises(ValueError, match="quarter boundary"):
        ObservationPeriod(date(2025, 2, 1), Frequency.QUARTERLY)
    with pytest.raises(ValueError, match="strictly increasing"):
        QuantitativeSeries((observed(1, "1"), replace(observed(1, "2"), id="duplicate")))
    with pytest.raises(ValueError, match="Series metadata"):
        QuantitativeSeries((observed(1, "1"), observed(2, "2", source="another-source")))
    with pytest.raises(ValueError, match="identities must be unique"):
        QuantitativeSeries((observed(1, "1"), replace(observed(2, "2"), id=observed(1, "1").id)))
