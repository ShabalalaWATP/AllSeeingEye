"""Invalid forecast histories and review claims fail closed at the domain boundary."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from ase.domain.doctrine import Confidence
from ase.domain.forecast_decisions import ForecastLedger
from ase.domain.forecast_ledger import (
    ConfidenceDimensions,
    DecisionMethod,
    ForecastState,
    PassageReference,
    ResolutionCriterion,
    evaluate_threshold,
)
from test_forecast_ledger import HORIZON, ISSUED, PASSAGE, decision, forecast, observation


def test_human_only_criterion_is_explicit_and_never_deterministically_resolved() -> None:
    row = forecast(criterion=ResolutionCriterion("Assess the final verified report"))
    assert evaluate_threshold(row, observation(), HORIZON) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"forecast_id": ""},
        {"issued_at": ISSUED.replace(tzinfo=None)},
        {"horizon_end": ISSUED},
        {"review_at": ISSUED - timedelta(seconds=1)},
        {"version": 0},
        {"supporting": ()},
        {"supporting": (PASSAGE, PASSAGE)},
        {"contrary": (PASSAGE,)},
        {"likelihood": "50%"},
        {"policy_version": "unknown"},
    ],
)
def test_forecast_definition_rejects_missing_time_quality_and_provenance(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        forecast(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"window_end": ISSUED - timedelta(seconds=1)},
        {"coverage_verified": "yes"},
        {"verification_reference": None},
        {"coverage_verified": True, "value": None, "passage": None},
        {"value": None, "passage": None},
        {"value": Decimal("NaN")},
        {"value": Decimal("1e25")},
    ],
)
def test_threshold_observation_rejects_invalid_capture(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        observation(**changes)


def test_criterion_rejects_unsupported_comparison_and_confidence_dimensions() -> None:
    with pytest.raises(ValueError, match="Unsupported threshold"):
        replace(forecast().criterion, direction="at_least")
    with pytest.raises(ValueError, match="confidence dimensions"):
        replace(
            forecast().confidence,
            source_quality="high",
        )
    assert (
        ConfidenceDimensions(
            Confidence.HIGH, Confidence.MODERATE, Confidence.LOW, "Known collection gap"
        ).coverage
        is Confidence.LOW
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "resolved"},
        {"outcome": 1},
        {"observation": "fabricated"},
        {"evidence": ("not-a-passage",)},
        {"recorded_at": ISSUED.replace(tzinfo=None)},
    ],
)
def test_review_record_rejects_untyped_inputs(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        decision(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"forecast_version_id": "unknown"},
        {"previous_decision_id": "unknown"},
        {"recorded_at": ISSUED - timedelta(seconds=1)},
        {"state": ForecastState.OPEN, "outcome": None, "observation": None, "evidence": ()},
        {
            "state": ForecastState.DUE,
            "recorded_at": HORIZON,
            "method": DecisionMethod.REVIEWER,
            "outcome": None,
            "observation": None,
            "evidence": (),
        },
        {
            "state": ForecastState.UNRESOLVED,
            "recorded_at": HORIZON,
            "method": DecisionMethod.THRESHOLD,
            "outcome": None,
            "observation": None,
            "evidence": (),
        },
        {"method": DecisionMethod.CLOCK, "observation": None},
        {"corrects_decision_id": "absent"},
        {"superseding_version_id": "forecast-v2"},
    ],
)
def test_first_review_rejects_invalid_state_and_authorship(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ForecastLedger((forecast(),)).append(decision(**changes))


def test_clock_review_cannot_claim_source_evidence() -> None:
    clock = decision(
        state=ForecastState.UNRESOLVED,
        recorded_at=HORIZON,
        method=DecisionMethod.CLOCK,
        outcome=None,
        observation=None,
    )
    with pytest.raises(ValueError, match="Clock transitions"):
        ForecastLedger((forecast(),)).append(clock)


def test_version_and_decision_history_links_are_strict() -> None:
    first = forecast()
    with pytest.raises(ValueError, match="one to 64"):
        ForecastLedger(())
    with pytest.raises(ValueError, match="typed"):
        ForecastLedger(("not-a-version",))
    with pytest.raises(ValueError, match="unique"):
        ForecastLedger((first, replace(first, version=2, supersedes_version_id=first.version_id)))
    with pytest.raises(ValueError, match="typed, unique"):
        ForecastLedger((first,), (decision(), decision()))
    with pytest.raises(ValueError, match="state cannot predate"):
        ForecastLedger((first,)).state_at(ISSUED - timedelta(seconds=1))
    assert ForecastLedger((first,)).current_version is first


def test_supersession_method_and_new_version_are_checked_together() -> None:
    initial = ForecastLedger((forecast(),))
    new = forecast(
        version=2,
        version_id="forecast-v2",
        claim_version_id="claim-v2",
        issued_at=ISSUED + timedelta(days=1),
        horizon_end=HORIZON + timedelta(days=1),
        review_at=HORIZON + timedelta(days=1),
        supersedes_version_id="forecast-v1",
    )
    with pytest.raises(ValueError, match="superseded decision"):
        initial.supersede(new, decision())
    with pytest.raises(ValueError, match="reviewer"):
        initial.supersede(
            new,
            decision(
                state=ForecastState.SUPERSEDED,
                method=DecisionMethod.CLOCK,
                recorded_at=ISSUED + timedelta(days=1),
                evidence=(),
                outcome=None,
                observation=None,
                superseding_version_id="forecast-v2",
            ),
        )


def test_corrections_cannot_fork_or_repeat_due_state() -> None:
    first = decision(method=DecisionMethod.REVIEWER, observation=None)
    ledger = ForecastLedger((forecast(),)).append(first)
    correction = decision(
        id="decision-2",
        previous_decision_id=first.id,
        method=DecisionMethod.REVIEWER,
        observation=None,
        corrects_decision_id=first.id,
        recorded_at=HORIZON,
    )
    with pytest.raises(ValueError, match="linked reviewer correction"):
        ledger.append(replace(correction, corrects_decision_id="wrong"))
    due = decision(
        state=ForecastState.DUE,
        method=DecisionMethod.CLOCK,
        recorded_at=HORIZON,
        evidence=(),
        outcome=None,
        observation=None,
    )
    with pytest.raises(ValueError, match="cannot be repeated"):
        ForecastLedger((forecast(),)).append(due).append(
            replace(due, id="decision-2", previous_decision_id=due.id)
        )


def test_pointers_are_bounded_and_nonempty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        PassageReference("", "evidence", "passage")
    with pytest.raises(ValueError, match="distinct"):
        forecast(contrary=(PASSAGE,))
    with pytest.raises(ValueError, match="cited evidence"):
        ForecastLedger((forecast(),)).append(
            decision(method=DecisionMethod.REVIEWER, observation=None, evidence=())
        )
