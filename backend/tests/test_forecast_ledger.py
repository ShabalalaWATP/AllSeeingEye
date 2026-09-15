"""Forecasts cannot silently resolve from weak or missing observations."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ase.domain.doctrine import Confidence, Probability
from ase.domain.forecast_decisions import ForecastDecision, ForecastLedger
from ase.domain.forecast_ledger import (
    ConfidenceDimensions,
    DecisionMethod,
    ForecastState,
    ForecastVersion,
    PassageReference,
    ResolutionCriterion,
    ThresholdDirection,
    ThresholdObservation,
    WindowAggregate,
    evaluate_threshold,
)

ISSUED = datetime(2026, 1, 1, tzinfo=UTC)
HORIZON = ISSUED + timedelta(days=7)
PASSAGE = PassageReference("report-v1", "evidence-1", "passage-1")


def forecast(**changes: object) -> ForecastVersion:
    values = {
        "forecast_id": "forecast-1",
        "version_id": "forecast-v1",
        "version": 1,
        "claim_id": "claim-1",
        "claim_version_id": "claim-v1",
        "report_version_id": "report-v1",
        "issued_at": ISSUED,
        "horizon_end": HORIZON,
        "review_at": HORIZON,
        "criterion": ResolutionCriterion(
            "Maximum verified weekly cases reaches 10",
            "cases",
            "public-statistics",
            "cases",
            Decimal("10"),
            ThresholdDirection.AT_LEAST,
            WindowAggregate.MAXIMUM,
        ),
        "likelihood": Probability.REALISTIC_POSSIBILITY,
        "confidence": ConfidenceDimensions(
            Confidence.MODERATE, Confidence.LOW, Confidence.MODERATE, "Sparse reporting"
        ),
        "supporting": (PASSAGE,),
        "contrary": (),
    }
    return ForecastVersion(**(values | changes))  # type: ignore[arg-type]


def observation(**changes: object) -> ThresholdObservation:
    values = {
        "metric_id": "cases",
        "source_id": "public-statistics",
        "unit": "cases",
        "aggregate": WindowAggregate.MAXIMUM,
        "value": Decimal("10"),
        "window_start": ISSUED,
        "window_end": ISSUED + timedelta(days=2),
        "coverage_verified": False,
        "verification_reference": "capture-1",
        "passage": PASSAGE,
    }
    return ThresholdObservation(**(values | changes))  # type: ignore[arg-type]


def decision(**changes: object) -> ForecastDecision:
    values = {
        "id": "decision-1",
        "forecast_version_id": "forecast-v1",
        "previous_decision_id": None,
        "recorded_at": ISSUED + timedelta(days=2),
        "state": ForecastState.RESOLVED,
        "method": DecisionMethod.THRESHOLD,
        "actor_id": "threshold-policy-v1",
        "reason": "Verified maximum reached the declared threshold",
        "evidence": (PASSAGE,),
        "outcome": True,
        "observation": observation(),
    }
    return ForecastDecision(**(values | changes))  # type: ignore[arg-type]


def test_threshold_crossing_resolves_at_inclusive_boundary_with_exact_citation() -> None:
    initial = ForecastLedger((forecast(),))
    resolved = initial.append(decision())
    assert initial.state_at(ISSUED + timedelta(days=2)) is ForecastState.OPEN
    assert resolved.state_at(ISSUED + timedelta(days=2)) is ForecastState.RESOLVED
    assert resolved.latest_decision("forecast-v1").evidence == (PASSAGE,)  # type: ignore[union-attr]
    with pytest.raises(FrozenInstanceError):
        resolved.versions[0].claim_id = "rewritten"  # type: ignore[misc]


def test_negative_outcome_needs_complete_verified_horizon_coverage() -> None:
    partial = observation(value=Decimal("9"))
    assert evaluate_threshold(forecast(), partial, HORIZON) is None
    complete = observation(value=Decimal("9"), window_end=HORIZON, coverage_verified=True)
    assert evaluate_threshold(forecast(), complete, HORIZON) is False
    assert evaluate_threshold(forecast(), complete, HORIZON - timedelta(hours=1)) is None
    resolved = ForecastLedger((forecast(),)).append(
        decision(recorded_at=HORIZON, outcome=False, observation=complete)
    )
    assert resolved.state_at(HORIZON) is ForecastState.RESOLVED


@pytest.mark.parametrize(
    "changes",
    [
        {"value": None, "passage": None, "verification_reference": None},
        {"source_id": "different-source"},
        {"unit": "people"},
        {"metric_id": "different-metric"},
        {"aggregate": WindowAggregate.MINIMUM},
        {"window_start": ISSUED - timedelta(days=1)},
        {"window_end": HORIZON + timedelta(seconds=1)},
    ],
)
def test_missing_or_mismatched_observation_cannot_resolve(changes: dict[str, object]) -> None:
    observed = observation(**changes)
    assert evaluate_threshold(forecast(), observed, HORIZON + timedelta(days=2)) is None
    with pytest.raises(ValueError, match="Deterministic outcome"):
        ForecastLedger((forecast(),)).append(
            decision(recorded_at=HORIZON + timedelta(days=2), observation=observed)
        )


def test_human_resolution_needs_cited_evidence_and_can_be_corrected_without_rewriting() -> None:
    first = decision(method=DecisionMethod.REVIEWER, actor_id="reviewer-1", observation=None)
    original = ForecastLedger((forecast(),)).append(first)
    correction = decision(
        id="decision-2",
        previous_decision_id=first.id,
        recorded_at=HORIZON + timedelta(days=1),
        method=DecisionMethod.REVIEWER,
        actor_id="reviewer-2",
        reason="A later verified correction overturns the initial assessment",
        outcome=False,
        observation=None,
        corrects_decision_id=first.id,
    )
    corrected = original.append(correction)
    assert [row.outcome for row in corrected.decisions] == [True, False]
    assert original.decisions == (first,)
    assert corrected.state_at(ISSUED + timedelta(days=3)) is ForecastState.RESOLVED
    with pytest.raises(ValueError, match="linked reviewer correction"):
        original.append(replace(correction, method=DecisionMethod.THRESHOLD))
    with pytest.raises(ValueError, match="cited evidence"):
        ForecastLedger((forecast(),)).append(replace(first, evidence=()))


def test_past_horizon_becomes_due_then_explicitly_unresolved() -> None:
    initial = ForecastLedger((forecast(),))
    assert initial.state_at(HORIZON) is ForecastState.DUE
    unresolved = initial.append(
        decision(
            recorded_at=HORIZON,
            state=ForecastState.UNRESOLVED,
            method=DecisionMethod.CLOCK,
            actor_id="clock-policy-v1",
            reason="No unambiguous observation by the horizon",
            evidence=(),
            outcome=None,
            observation=None,
        )
    )
    assert unresolved.state_at(HORIZON) is ForecastState.UNRESOLVED
    with pytest.raises(ValueError, match="before its horizon"):
        initial.append(replace(unresolved.decisions[0], recorded_at=HORIZON - timedelta(seconds=1)))


def test_supersession_links_versions_and_keeps_old_decisions() -> None:
    original = ForecastLedger((forecast(),))
    new = forecast(
        version=2,
        version_id="forecast-v2",
        claim_version_id="claim-v2",
        issued_at=ISSUED + timedelta(days=1),
        horizon_end=HORIZON + timedelta(days=1),
        review_at=HORIZON + timedelta(days=1),
        supersedes_version_id="forecast-v1",
    )
    superseding = decision(
        recorded_at=ISSUED + timedelta(days=1),
        state=ForecastState.SUPERSEDED,
        method=DecisionMethod.REVIEWER,
        actor_id="reviewer-1",
        reason="Claim wording and horizon have changed",
        evidence=(),
        outcome=None,
        observation=None,
        superseding_version_id="forecast-v2",
    )
    later = original.supersede(new, superseding)
    assert later.state_at(ISSUED) is ForecastState.OPEN
    assert later.latest_decision("forecast-v1") is superseding
    assert later.state_at(ISSUED + timedelta(days=1)) is ForecastState.OPEN
    with pytest.raises(ValueError, match="closed"):
        later.append(
            replace(decision(), id="decision-after-close", previous_decision_id=superseding.id)
        )
    with pytest.raises(ValueError, match="explicit supersession"):
        ForecastLedger((forecast(), new))
    with pytest.raises(ValueError, match="atomically"):
        original.append(superseding)


def test_non_resolution_cannot_carry_a_hidden_outcome() -> None:
    with pytest.raises(ValueError, match="Only a resolved"):
        ForecastLedger((forecast(),)).append(
            decision(
                state=ForecastState.SUPERSEDED,
                method=DecisionMethod.REVIEWER,
                superseding_version_id="forecast-v2",
            )
        )


def test_forecast_rejects_ambiguous_criterion_and_non_phia_probability() -> None:
    with pytest.raises(ValueError, match="threshold criterion needs"):
        ResolutionCriterion("Cases rise", threshold=Decimal("10"))
    with pytest.raises(ValueError, match="direction must match"):
        replace(
            forecast().criterion,
            aggregate=WindowAggregate.MINIMUM,
        )
    with pytest.raises(ValueError, match="PHIA band"):
        forecast(likelihood="50%")
