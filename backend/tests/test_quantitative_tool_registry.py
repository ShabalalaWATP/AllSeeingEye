"""The model can request calculations, never supply data or executable work."""

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from fractions import Fraction

import pytest
from pydantic import ValidationError

from ase.application.analysis.spec import parse_analysis_spec
from ase.application.analysis.tool_registry import AuthorisedQuantitativeSet, execute_analysis
from ase.domain.quantitative_calculations import FORMULA_VERSION, Formula
from ase.domain.quantitative_observations import (
    Frequency,
    MeasureKind,
    ObservationPeriod,
    QuantitativeObservation,
    QuantitativeSeries,
    SeasonalAdjustment,
)


def observation(
    month: int,
    value: str | None,
    *,
    entity: str = "GB",
    series: str = "series-gb",
    measure: str = "cases",
    unit: str = "cases",
    kind: MeasureKind = MeasureKind.FLOW,
) -> QuantitativeObservation:
    return QuantitativeObservation(
        id=f"{series}:{month}",
        series_id=series,
        measure_id=measure,
        entity_id=entity,
        period=ObservationPeriod(date(2025, month, 1), Frequency.MONTHLY),
        value=Decimal(value) if value is not None else None,
        unit=unit,
        currency=None,
        adjustment=SeasonalAdjustment.UNADJUSTED,
        vintage="2026-01",
        measure_kind=kind,
        source_id="official-statistics",
        evidence_id=f"evidence:{series}:{month}",
        reference=f"https://example.test/{series}/{month}",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def proposal(operation: str, **parameters: object) -> str:
    return json.dumps({"schema_version": 1, "operation": operation, **parameters})


def set_of(*series: QuantitativeSeries) -> AuthorisedQuantitativeSet:
    return AuthorisedQuantitativeSet(series)


def test_change_uses_only_authorised_observations_and_exact_receipt() -> None:
    early, late = observation(1, "0.1"), observation(2, "0.3")
    inputs = set_of(QuantitativeSeries((early, late)))
    spec = parse_analysis_spec(proposal("percentage_change", observation_ids=[early.id, late.id]))

    execution = execute_analysis(spec, inputs)

    assert execution.operation is Formula.PERCENTAGE_CHANGE
    assert execution.schema_version == 1
    assert execution.results[0].value == Fraction(200)
    assert execution.results[0].receipt.version == FORMULA_VERSION
    assert execution.results[0].receipt.exact_numerator == 200
    assert [item.observation_id for item in execution.results[0].receipt.inputs] == [
        early.id,
        late.id,
    ]
    assert execution.evidence_ids == (early.evidence_id, late.evidence_id)
    assert execution.source_ids == (early.source_id,)
    assert execute_analysis(
        parse_analysis_spec(proposal("absolute_change", observation_ids=[early.id, late.id])),
        inputs,
    ).results[0].value == Fraction(1, 5)


def test_series_operations_retain_per_point_formula_and_coverage() -> None:
    items = tuple(observation(month, value) for month, value in ((1, "2"), (2, "4"), (3, "8")))
    inputs = set_of(QuantitativeSeries(items))
    index = execute_analysis(
        parse_analysis_spec(
            proposal(
                "index_base_100", series_ids=[items[0].series_id], base_period_start="2025-01-01"
            )
        ),
        inputs,
    )
    rolling = execute_analysis(
        parse_analysis_spec(
            proposal("rolling_mean", series_ids=[items[0].series_id], window_length=2)
        ),
        inputs,
    )
    total = execute_analysis(
        parse_analysis_spec(
            proposal("rolling_sum", series_ids=[items[0].series_id], window_length=2)
        ),
        inputs,
    )
    assert [result.value for result in index.results] == [100, 200, 400]
    assert [result.value for result in rolling.results] == [3, 6]
    assert [result.value for result in total.results] == [6, 12]
    assert rolling.results[0].receipt.coverage == (items[0].period, items[1].period)
    assert (
        rolling.results[0].receipt.expression == "sum(complete contiguous window) / window_length"
    )
    assert rolling.evidence_ids == tuple(item.evidence_id for item in items)


def test_rate_and_aligned_comparison_use_fixed_operations() -> None:
    numerator = observation(1, "1")
    denominator = observation(
        1, "3", series="population", measure="population", unit="people", kind=MeasureKind.STOCK
    )
    rate_result = execute_analysis(
        parse_analysis_spec(
            proposal("rate", observation_ids=[numerator.id, denominator.id], scale=1_000)
        ),
        set_of(QuantitativeSeries((numerator,)), QuantitativeSeries((denominator,))),
    ).results[0]
    assert rate_result.value == Fraction(1_000, 3)
    assert rate_result.receipt.scale == 1_000
    assert rate_result.unit == "cases per 1000 people"

    left = QuantitativeSeries((observation(1, "2"), observation(2, "4")))
    right = QuantitativeSeries(
        (
            observation(1, "3", entity="US", series="series-us"),
            observation(2, "8", entity="US", series="series-us"),
        )
    )
    inputs = set_of(left, right)
    absolute = execute_analysis(
        parse_analysis_spec(proposal("aligned_absolute", series_ids=["series-gb", "series-us"])),
        inputs,
    )
    percentage = execute_analysis(
        parse_analysis_spec(proposal("aligned_percentage", series_ids=["series-gb", "series-us"])),
        inputs,
    )
    assert [result.value for result in absolute.results] == [1, 4]
    assert [result.value for result in percentage.results] == [50, 100]


@pytest.mark.parametrize(
    "payload",
    [
        proposal("eval", observation_ids=["series-gb:1", "series-gb:2"]),
        proposal("absolute_change", observation_ids=["series-gb:1", "series-gb:2"], code="1+1"),
        proposal(
            "absolute_change", observation_ids=["series-gb:1", "series-gb:2"], url="https://a"
        ),
        proposal("absolute_change", observation_ids=["series-gb:1", "series-gb:2"], value=999),
        proposal("absolute_change", observation_ids=["series-gb:1", "series-gb:2"], scale=1),
        proposal("rate", observation_ids=["series-gb:1", "population:1"], scale=7),
        proposal("rolling_sum", series_ids=["series-gb"], window_length=1),
        proposal("aligned_absolute", series_ids=["series-gb", "series-gb"]),
        proposal("index_base_100", series_ids=["series-gb"]),
        proposal("absolute_change", observation_ids=["series-gb:1"]),
        proposal("absolute_change", observation_ids=["series-gb:1", " series-gb:2"]),
        json.dumps({"schema_version": 2, "operation": "rate", "observation_ids": []}),
        "[]",
    ],
)
def test_model_proposal_rejects_unsupported_or_malicious_shape(payload: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        parse_analysis_spec(payload)


def test_unknown_or_missing_data_fail_closed() -> None:
    first, second = observation(1, "2"), observation(2, None)
    inputs = set_of(QuantitativeSeries((first, second)))
    with pytest.raises(ValueError, match="unavailable"):
        execute_analysis(
            parse_analysis_spec(
                proposal("absolute_change", observation_ids=[first.id, "unseen:2"])
            ),
            inputs,
        )
    with pytest.raises(ValueError, match="missing"):
        execute_analysis(
            parse_analysis_spec(proposal("absolute_change", observation_ids=[first.id, second.id])),
            inputs,
        )
    with pytest.raises(ValueError, match="base period is absent"):
        execute_analysis(
            parse_analysis_spec(
                proposal(
                    "index_base_100", series_ids=[first.series_id], base_period_start="2024-01-01"
                )
            ),
            inputs,
        )


def test_input_snapshot_has_bounded_unique_typed_identities() -> None:
    first = observation(1, "2")
    with pytest.raises(ValueError, match="unique"):
        set_of(QuantitativeSeries((first,)), QuantitativeSeries((first,)))
    with pytest.raises(ValueError, match="typed"):
        set_of("not a series")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="one to 16"):
        set_of()
    with pytest.raises(ValueError, match="unique"):
        set_of(
            QuantitativeSeries((first,)),
            QuantitativeSeries((replace(first, series_id="another-series", entity_id="US"),)),
        )


def test_spec_size_and_rate_denominator_limits() -> None:
    with pytest.raises(ValueError, match="bounded JSON"):
        parse_analysis_spec("x" * 4097)
    numerator = observation(1, "1")
    denominator = observation(
        1, "0", series="population", measure="population", unit="people", kind=MeasureKind.STOCK
    )
    with pytest.raises(ValueError, match="positive denominator"):
        execute_analysis(
            parse_analysis_spec(
                proposal("rate", observation_ids=[numerator.id, denominator.id], scale=1)
            ),
            set_of(QuantitativeSeries((numerator,)), QuantitativeSeries((denominator,))),
        )
