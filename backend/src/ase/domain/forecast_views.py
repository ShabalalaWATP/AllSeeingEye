"""Counts of forecast versions, without converting PHIA labels to probabilities."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ase.domain.doctrine import Probability
from ase.domain.forecast_decisions import ForecastLedger
from ase.domain.forecast_ledger import ForecastState, ForecastVersion


@dataclass(frozen=True, slots=True)
class ForecastIndex:
    ledger_id: UUID
    report_id: UUID
    report_version: int
    title: str


@dataclass(frozen=True, slots=True)
class ForecastWatch:
    ledger_id: UUID
    report_id: UUID
    report_version: int
    title: str
    version_id: str
    review_at: datetime
    horizon_end: datetime
    state: ForecastState
    review_due: bool
    reminded_at: datetime | None
    team_id: UUID | None


@dataclass(slots=True)
class ForecastBandCount:
    likelihood: Probability
    resolved_true: int = 0
    resolved_false: int = 0
    unresolved: int = 0
    open: int = 0
    due: int = 0
    superseded: int = 0
    resolved_denominator: int = 0


@dataclass(frozen=True, slots=True)
class ForecastCounts:
    since: datetime
    until: datetime
    bands: tuple[ForecastBandCount, ...]
    forecast_versions: int
    counting_unit: str = "forecast version, by issue time, using its latest decision once"
    caveat: str = (
        "Related versions may not be independent observations. The cohort can be small or "
        "selective. PHIA bands are not calibrated probabilities. Only true plus false form "
        "the resolved denominator; no accuracy percentages are calculated."
    )


def version_state(
    history: ForecastLedger, version: ForecastVersion, now: datetime
) -> ForecastState:
    latest = history.latest_decision(version.version_id)
    if latest is not None:
        return latest.state
    return ForecastState.DUE if now >= version.horizon_end else ForecastState.OPEN


def count_versions(
    histories: tuple[ForecastLedger, ...],
    since: datetime,
    until: datetime,
    now: datetime,
) -> ForecastCounts:
    counts = {band: ForecastBandCount(band) for band in Probability}
    total = 0
    for history in histories:
        for version in history.versions:
            if not since <= version.issued_at < until:
                continue
            total += 1
            row = counts[version.likelihood]
            state = version_state(history, version, now)
            if state is ForecastState.RESOLVED:
                decision = history.latest_decision(version.version_id)
                if decision is not None and decision.outcome is True:
                    row.resolved_true += 1
                else:
                    row.resolved_false += 1
                row.resolved_denominator += 1
            else:
                setattr(row, state.value, getattr(row, state.value) + 1)
    return ForecastCounts(since, until, tuple(counts.values()), total)
