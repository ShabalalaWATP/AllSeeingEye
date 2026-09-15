"""Validated append-only forecast state changes and version supersession."""

from dataclasses import dataclass
from datetime import datetime

from ase.domain.forecast_ledger import (
    DecisionMethod,
    ForecastState,
    ForecastVersion,
    PassageReference,
    ThresholdObservation,
    _text,
    _time,
    evaluate_threshold,
)


@dataclass(frozen=True, slots=True)
class ForecastDecision:
    id: str
    forecast_version_id: str
    previous_decision_id: str | None
    recorded_at: datetime
    state: ForecastState
    method: DecisionMethod
    actor_id: str
    reason: str
    evidence: tuple[PassageReference, ...] = ()
    outcome: bool | None = None
    observation: ThresholdObservation | None = None
    corrects_decision_id: str | None = None
    superseding_version_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("id", "forecast_version_id", "actor_id"):
            _text(getattr(self, name), name)
        _text(self.reason, "decision reason", 2000)
        _time(self.recorded_at, "decision time")
        if not isinstance(self.state, ForecastState) or not isinstance(self.method, DecisionMethod):
            raise ValueError("Unknown decision state or method")
        for name in ("previous_decision_id", "corrects_decision_id", "superseding_version_id"):
            value = getattr(self, name)
            if value is not None:
                _text(value, name)
        if (
            type(self.evidence) is not tuple
            or len(self.evidence) > 64
            or any(not isinstance(ref, PassageReference) for ref in self.evidence)
        ):
            raise ValueError("Decision evidence must be bounded frozen passages")
        if self.outcome is not None and type(self.outcome) is not bool:
            raise ValueError("A resolved outcome is true or false")
        if self.observation is not None and not isinstance(self.observation, ThresholdObservation):
            raise ValueError("Threshold observation must be typed")


@dataclass(frozen=True, slots=True)
class ForecastLedger:
    versions: tuple[ForecastVersion, ...]
    decisions: tuple[ForecastDecision, ...] = ()

    def __post_init__(self) -> None:
        _validate_versions(self.versions)
        _validate_history(self.versions, self.decisions)

    @property
    def current_version(self) -> ForecastVersion:
        return self.versions[-1]

    def latest_decision(self, version_id: str) -> ForecastDecision | None:
        return next(
            (row for row in reversed(self.decisions) if row.forecast_version_id == version_id),
            None,
        )

    def state_at(self, when: datetime) -> ForecastState:
        _time(when, "state time")
        version = next((row for row in reversed(self.versions) if row.issued_at <= when), None)
        if version is None:
            raise ValueError("Forecast state cannot predate its first issue")
        decision = next(
            (
                row
                for row in reversed(self.decisions)
                if row.forecast_version_id == version.version_id and row.recorded_at <= when
            ),
            None,
        )
        if decision is not None:
            return decision.state
        return ForecastState.DUE if when >= version.horizon_end else ForecastState.OPEN

    def append(self, decision: ForecastDecision) -> "ForecastLedger":
        return ForecastLedger(self.versions, (*self.decisions, decision))

    def supersede(
        self, new_version: ForecastVersion, decision: ForecastDecision
    ) -> "ForecastLedger":
        if decision.state is not ForecastState.SUPERSEDED:
            raise ValueError("Supersession needs a superseded decision")
        return ForecastLedger((*self.versions, new_version), (*self.decisions, decision))


def _validate_versions(rows: tuple[ForecastVersion, ...]) -> None:
    if type(rows) is not tuple or not 1 <= len(rows) <= 64:
        raise ValueError("Forecast ledger needs one to 64 immutable versions")
    if any(not isinstance(row, ForecastVersion) for row in rows):
        raise ValueError("Forecast versions must be typed")
    if len({row.version_id for row in rows}) != len(rows):
        raise ValueError("Forecast version IDs must be unique")
    for number, row in enumerate(rows, 1):
        if row.version != number or row.forecast_id != rows[0].forecast_id:
            raise ValueError("Forecast versions must be consecutive for one identity")
        previous = rows[number - 2] if number > 1 else None
        if row.supersedes_version_id != (previous.version_id if previous else None):
            raise ValueError("Forecast versions require consecutive supersession links")
        if previous is not None and row.issued_at <= previous.issued_at:
            raise ValueError("A new forecast version must be issued later")


def _validate_history(
    versions: tuple[ForecastVersion, ...], decisions: tuple[ForecastDecision, ...]
) -> None:
    if type(decisions) is not tuple or len(decisions) > 256:
        raise ValueError("Forecast ledger decisions exceed the immutable cap")
    by_version = {row.version_id: row for row in versions}
    latest: dict[str, ForecastDecision] = {}
    ids: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, ForecastDecision) or decision.id in ids:
            raise ValueError("Forecast decisions need typed, unique IDs")
        version = by_version.get(decision.forecast_version_id)
        if version is None:
            raise ValueError("Decision references an unknown forecast version")
        _validate_decision(version, latest.get(version.version_id), decision)
        latest[version.version_id] = decision
        ids.add(decision.id)
    for new in versions[1:]:
        prior_decision = latest.get(new.supersedes_version_id or "")
        if (
            prior_decision is None
            or prior_decision.state is not ForecastState.SUPERSEDED
            or prior_decision.superseding_version_id != new.version_id
            or new.issued_at < prior_decision.recorded_at
        ):
            raise ValueError("A later version needs an explicit supersession decision")
    for decision in decisions:
        if decision.state is ForecastState.SUPERSEDED:
            new_version = by_version.get(decision.superseding_version_id or "")
            if (
                new_version is None
                or new_version.supersedes_version_id != decision.forecast_version_id
            ):
                raise ValueError("Supersession must atomically name its new version")


def _validate_decision(
    version: ForecastVersion, prior: ForecastDecision | None, decision: ForecastDecision
) -> None:
    _validate_transition(version, prior, decision)
    _validate_state(version, decision)
    _validate_supersession(decision)


def _validate_transition(
    version: ForecastVersion, prior: ForecastDecision | None, decision: ForecastDecision
) -> None:
    if decision.previous_decision_id != (prior.id if prior else None):
        raise ValueError("Decision must link to the last decision for this version")
    if decision.recorded_at < version.issued_at or (
        prior is not None and decision.recorded_at < prior.recorded_at
    ):
        raise ValueError("Decision cannot predate the forecast or prior review")
    old = prior.state if prior else ForecastState.OPEN
    if old in (ForecastState.RESOLVED, ForecastState.UNRESOLVED):
        if (
            prior is None
            or decision.state not in (ForecastState.RESOLVED, ForecastState.UNRESOLVED)
            or decision.corrects_decision_id != prior.id
            or decision.method is not DecisionMethod.REVIEWER
        ):
            raise ValueError("A final decision changes only by linked reviewer correction")
    elif old is ForecastState.SUPERSEDED:
        raise ValueError("A superseded forecast version is closed")
    elif decision.corrects_decision_id is not None:
        raise ValueError("Only a final decision may be corrected")
    if old is ForecastState.DUE and decision.state is ForecastState.DUE:
        raise ValueError("A due decision cannot be repeated")


def _validate_state(version: ForecastVersion, decision: ForecastDecision) -> None:
    if decision.state is ForecastState.OPEN:
        raise ValueError("Open is the initial state, not a decision")
    if decision.state is not ForecastState.RESOLVED and (
        decision.outcome is not None or decision.observation is not None
    ):
        raise ValueError("Only a resolved decision may retain an outcome or observation")
    if (
        decision.state in (ForecastState.DUE, ForecastState.UNRESOLVED)
        and decision.recorded_at < version.horizon_end
    ):
        raise ValueError("A forecast cannot be due or unresolved before its horizon")
    if decision.state is ForecastState.DUE and decision.method is not DecisionMethod.CLOCK:
        raise ValueError("Due is a clock transition")
    if decision.state is ForecastState.RESOLVED:
        _validate_resolved(version, decision)
    elif decision.evidence and decision.state is not ForecastState.UNRESOLVED:
        raise ValueError("Only resolution or unresolved review retains evidence")
    if decision.state is ForecastState.UNRESOLVED and decision.method not in (
        DecisionMethod.REVIEWER,
        DecisionMethod.CLOCK,
    ):
        raise ValueError("Unresolved status requires review or a passed horizon")
    if decision.state is ForecastState.UNRESOLVED and (
        decision.method is DecisionMethod.CLOCK and decision.evidence
    ):
        raise ValueError("Clock transitions cannot claim reviewed evidence")


def _validate_resolved(version: ForecastVersion, decision: ForecastDecision) -> None:
    if decision.outcome is None or not decision.evidence:
        raise ValueError("Resolution needs an outcome and cited evidence")
    if decision.method is DecisionMethod.THRESHOLD:
        observed = decision.observation
        if (
            observed is None
            or evaluate_threshold(version, observed, decision.recorded_at) is not decision.outcome
            or decision.evidence != (observed.passage,)
        ):
            raise ValueError("Deterministic outcome must match verified threshold evidence")
    elif decision.method is not DecisionMethod.REVIEWER or decision.observation is not None:
        raise ValueError("Non-deterministic resolution needs a human reviewer")


def _validate_supersession(decision: ForecastDecision) -> None:
    if decision.state is ForecastState.SUPERSEDED:
        if (
            decision.method is not DecisionMethod.REVIEWER
            or decision.superseding_version_id is None
        ):
            raise ValueError("Supersession needs a reviewer and a new version")
    elif decision.superseding_version_id is not None:
        raise ValueError("Only supersession may name a new version")
