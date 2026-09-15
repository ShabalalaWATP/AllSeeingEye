"""Indicator version and observation invariants reject ambiguous source states."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from ase.domain.forecast_ledger import ThresholdDirection
from ase.domain.indicator_ledger import IndicatorLedger, IndicatorStatus
from test_indicator_ledger import ISSUED, PASSAGE, indicator, reading


@pytest.mark.parametrize(
    "changes",
    [
        {"version": 0},
        {"expected_update_hours": 0},
        {"expected_update_hours": 24 * 367},
        {"direction": "at_least"},
        {"policy_version": "unknown"},
        {"issued_at": ISSUED.replace(tzinfo=None)},
    ],
)
def test_indicator_definition_rejects_unbounded_or_untyped_fields(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        indicator(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"observed_at": ISSUED + timedelta(hours=3)},
        {"missing_reason": "No publication"},
        {"value": None, "passage": PASSAGE, "missing_reason": "No publication"},
        {"value": Decimal("Infinity")},
        {"recorded_at": ISSUED.replace(tzinfo=None)},
    ],
)
def test_indicator_reading_rejects_conflicting_value_and_capture_shapes(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        reading(**changes)


def test_indicator_without_version_or_with_bad_links_fails_closed() -> None:
    first = indicator()
    with pytest.raises(ValueError, match="one to 64"):
        IndicatorLedger(())
    with pytest.raises(ValueError, match="typed"):
        IndicatorLedger(("wrong-type",))
    with pytest.raises(ValueError, match="unique"):
        IndicatorLedger((first, replace(first, version=2, supersedes_version_id=first.version_id)))
    with pytest.raises(ValueError, match="consecutive"):
        IndicatorLedger(
            (first, replace(first, version=2, version_id="v2", supersedes_version_id=None))
        )
    with pytest.raises(ValueError, match="cannot predate"):
        IndicatorLedger((first,)).evaluate_at(ISSUED - timedelta(seconds=1))


def test_indicator_reading_order_and_identity_are_checked() -> None:
    first = reading()
    with pytest.raises(ValueError, match="typed unique IDs"):
        IndicatorLedger((indicator(),), (first, first))
    with pytest.raises(ValueError, match="capture time"):
        IndicatorLedger(
            (indicator(),),
            (
                first,
                reading(
                    id="reading-2",
                    observed_at=ISSUED + timedelta(minutes=30),
                    recorded_at=ISSUED + timedelta(hours=1),
                ),
            ),
        )


def test_at_most_threshold_handles_boundary_and_explicit_absence() -> None:
    row = indicator(threshold=Decimal("10"), direction=ThresholdDirection.AT_MOST)
    exact = IndicatorLedger((row,)).append(reading(value=Decimal("10")))
    assert exact.evaluate_at(ISSUED + timedelta(hours=2)).status is IndicatorStatus.MET
    above = IndicatorLedger((row,)).append(reading(value=Decimal("10.01")))
    result = above.evaluate_at(ISSUED + timedelta(hours=2))
    assert result.status is IndicatorStatus.NOT_MET
    assert "does not meet" in result.reason
