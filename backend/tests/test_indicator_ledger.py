"""Indicators expose source absence and late corrections without false certainty."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ase.domain.forecast_ledger import PassageReference, ThresholdDirection
from ase.domain.indicator_ledger import (
    IndicatorLedger,
    IndicatorReading,
    IndicatorStatus,
    IndicatorVersion,
)

ISSUED = datetime(2026, 1, 1, tzinfo=UTC)
PASSAGE = PassageReference("report-v1", "evidence-1", "passage-1")


def indicator(**changes: object) -> IndicatorVersion:
    values = {
        "indicator_id": "indicator-1",
        "version_id": "indicator-v1",
        "version": 1,
        "condition": "Reported weekly cases reach ten",
        "metric_id": "cases",
        "unit": "cases",
        "source_id": "public-statistics",
        "source_capability": "Publishes a verified case count each day",
        "expected_update_hours": 24,
        "issued_at": ISSUED,
        "threshold": Decimal("10"),
        "direction": ThresholdDirection.AT_LEAST,
    }
    return IndicatorVersion(**(values | changes))  # type: ignore[arg-type]


def reading(**changes: object) -> IndicatorReading:
    values = {
        "id": "reading-1",
        "indicator_version_id": "indicator-v1",
        "observed_at": ISSUED + timedelta(hours=1),
        "recorded_at": ISSUED + timedelta(hours=2),
        "unit": "cases",
        "value": Decimal("10"),
        "passage": PASSAGE,
        "verification_reference": "capture-1",
    }
    return IndicatorReading(**(values | changes))  # type: ignore[arg-type]


def test_no_source_data_is_unknown_and_missing_reading_is_not_false() -> None:
    ledger = IndicatorLedger((indicator(),))
    empty = ledger.evaluate_at(ISSUED + timedelta(hours=2))
    assert empty.status is IndicatorStatus.UNKNOWN and empty.reading_id is None
    missing = reading(
        value=None,
        passage=None,
        verification_reference=None,
        missing_reason="Provider did not publish this interval",
    )
    unknown = ledger.append(missing).evaluate_at(ISSUED + timedelta(hours=2))
    assert unknown.status is IndicatorStatus.UNKNOWN
    assert unknown.reading_id == missing.id


def test_threshold_boundary_and_staleness_are_explicit() -> None:
    ledger = IndicatorLedger((indicator(),)).append(reading())
    assert ledger.evaluate_at(ISSUED + timedelta(hours=2)).status is IndicatorStatus.MET
    assert ledger.evaluate_at(ISSUED + timedelta(hours=26)).status is IndicatorStatus.STALE
    below = IndicatorLedger((indicator(),)).append(reading(value=Decimal("9.999")))
    assert below.evaluate_at(ISSUED + timedelta(hours=2)).status is IndicatorStatus.NOT_MET


def test_late_correction_changes_current_projection_but_preserves_history() -> None:
    first = reading(value=Decimal("8"))
    original = IndicatorLedger((indicator(),)).append(first)
    correction = reading(
        id="reading-2",
        value=Decimal("12"),
        recorded_at=ISSUED + timedelta(hours=3),
        corrects_reading_id=first.id,
    )
    corrected = original.append(correction)
    assert original.evaluate_at(ISSUED + timedelta(hours=4)).status is IndicatorStatus.NOT_MET
    assert corrected.evaluate_at(ISSUED + timedelta(hours=2)).status is IndicatorStatus.NOT_MET
    assert corrected.evaluate_at(ISSUED + timedelta(hours=4)).status is IndicatorStatus.MET
    assert corrected.readings == (first, correction)
    with pytest.raises(FrozenInstanceError):
        first.value = Decimal("12")  # type: ignore[misc]


def test_late_correction_of_older_observation_does_not_override_newer_observation() -> None:
    old = reading(value=Decimal("10"))
    new = reading(
        id="reading-2",
        observed_at=ISSUED + timedelta(hours=2),
        recorded_at=ISSUED + timedelta(hours=3),
        value=Decimal("8"),
    )
    old_correction = reading(
        id="reading-3",
        value=Decimal("11"),
        recorded_at=ISSUED + timedelta(hours=4),
        corrects_reading_id=old.id,
    )
    ledger = IndicatorLedger((indicator(),), (old, new, old_correction))
    result = ledger.evaluate_at(ISSUED + timedelta(hours=4))
    assert result.status is IndicatorStatus.NOT_MET and result.reading_id == new.id


def test_indicator_version_supersession_retains_old_observations() -> None:
    initial = IndicatorLedger((indicator(),)).append(reading())
    new = indicator(
        version=2,
        version_id="indicator-v2",
        threshold=Decimal("12"),
        issued_at=ISSUED + timedelta(hours=3),
        supersedes_version_id="indicator-v1",
    )
    updated = initial.supersede(new)
    assert initial.evaluate_at(ISSUED + timedelta(hours=4)).status is IndicatorStatus.MET
    assert updated.evaluate_at(ISSUED + timedelta(hours=2)).status is IndicatorStatus.MET
    assert updated.evaluate_at(ISSUED + timedelta(hours=4)).status is IndicatorStatus.UNKNOWN
    assert len(updated.readings) == 1
    with pytest.raises(ValueError, match="new-period observations"):
        updated.append(
            reading(
                id="late-old-version",
                observed_at=ISSUED + timedelta(hours=4),
                recorded_at=ISSUED + timedelta(hours=5),
            )
        )


@pytest.mark.parametrize(
    "bad",
    [
        {"unit": "people"},
        {"indicator_version_id": "unknown-version"},
        {"observed_at": ISSUED - timedelta(hours=1)},
    ],
)
def test_reading_rejects_mismatched_version_unit_or_time(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        IndicatorLedger((indicator(),)).append(reading(**bad))


def test_correction_must_link_prior_same_observation_and_cannot_fork() -> None:
    first = reading()
    ledger = IndicatorLedger((indicator(),)).append(first)
    with pytest.raises(ValueError, match="correction link"):
        ledger.append(reading(id="duplicate-time", recorded_at=ISSUED + timedelta(hours=3)))
    with pytest.raises(ValueError, match="Correction must link"):
        ledger.append(reading(id="wrong", corrects_reading_id="missing"))
    corrected = ledger.append(
        reading(
            id="reading-2",
            recorded_at=ISSUED + timedelta(hours=3),
            corrects_reading_id=first.id,
        )
    )
    with pytest.raises(ValueError, match="Correction must link"):
        corrected.append(
            reading(
                id="fork",
                recorded_at=ISSUED + timedelta(hours=4),
                corrects_reading_id=first.id,
            )
        )


def test_non_numeric_condition_remains_unknown_despite_numeric_observation() -> None:
    plain = indicator(threshold=None, direction=None)
    result = IndicatorLedger((plain,)).append(reading()).evaluate_at(ISSUED + timedelta(hours=2))
    assert result.status is IndicatorStatus.UNKNOWN
    assert "No deterministic threshold" in result.reason


def test_missing_and_provenance_shapes_are_validated() -> None:
    with pytest.raises(ValueError, match="explicit reason"):
        reading(value=None, passage=None, verification_reference=None)
    with pytest.raises(ValueError, match="verification receipt"):
        reading(verification_reference=None)
    with pytest.raises(ValueError, match="set together"):
        indicator(direction=None)
    with pytest.raises(ValueError, match="finite"):
        indicator(threshold=Decimal("NaN"))
    with pytest.raises(ValueError, match="later"):
        IndicatorLedger(
            (
                indicator(),
                replace(
                    indicator(),
                    version=2,
                    version_id="indicator-v2",
                    supersedes_version_id="indicator-v1",
                ),
            )
        )
