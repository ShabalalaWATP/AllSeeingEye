"""Cohorts count frozen versions and their latest state, never decision rows."""

from datetime import timedelta

from ase.domain.forecast_decisions import ForecastLedger
from ase.domain.forecast_ledger import DecisionMethod, ForecastState
from ase.domain.forecast_views import count_versions
from test_forecast_ledger import HORIZON, ISSUED, decision, forecast


def test_open_due_unresolved_and_correction_have_distinct_denominators():
    original = forecast()
    resolved = ForecastLedger((original,)).append(decision())
    corrected = resolved.append(
        decision(
            id="correction",
            previous_decision_id="decision-1",
            corrects_decision_id="decision-1",
            method=DecisionMethod.REVIEWER,
            recorded_at=HORIZON,
            outcome=False,
            observation=None,
        )
    )
    unresolved = ForecastLedger((forecast(forecast_id="f2", version_id="v2"),)).append(
        decision(
            state=ForecastState.UNRESOLVED,
            forecast_version_id="v2",
            method=DecisionMethod.REVIEWER,
            recorded_at=HORIZON,
            evidence=(),
            outcome=None,
            observation=None,
        )
    )
    due = ForecastLedger((forecast(forecast_id="f3", version_id="v3"),))
    still_open = ForecastLedger(
        (forecast(forecast_id="f4", version_id="v4", horizon_end=HORIZON + timedelta(days=5)),)
    )
    counts = count_versions((corrected, unresolved, due, still_open), ISSUED, HORIZON, HORIZON)
    row = next(row for row in counts.bands if row.likelihood == original.likelihood)
    assert (row.resolved_true, row.resolved_false, row.unresolved, row.due, row.open) == (
        0,
        1,
        1,
        1,
        1,
    )
    assert row.resolved_denominator == 1 and counts.forecast_versions == 4
    assert sum(row.resolved_denominator for row in counts.bands) == 1
    assert (
        count_versions((corrected,), ISSUED - timedelta(days=1), ISSUED, HORIZON).forecast_versions
        == 0
    )
