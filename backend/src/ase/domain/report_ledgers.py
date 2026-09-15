"""Scope and exact frozen claim anchor for a retained forecast or indicator ledger."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from ase.domain.forecast_decisions import ForecastDecision, ForecastLedger
from ase.domain.forecast_ledger import ForecastVersion, PassageReference
from ase.domain.indicator_ledger import IndicatorLedger, IndicatorReading, IndicatorVersion

LedgerEntry = ForecastVersion | ForecastDecision | IndicatorVersion | IndicatorReading
MAX_REPORT_LEDGER_ENTRIES = 512


class LedgerKind(StrEnum):
    FORECAST = "forecast"
    INDICATOR = "indicator"


@dataclass(frozen=True, slots=True)
class ReportLedgerAnchor:
    id: UUID
    kind: LedgerKind
    report_id: UUID
    report_version_id: UUID
    claim_id: UUID
    claim_revision_id: UUID
    owner_id: UUID
    team_id: UUID | None
    created_at: datetime
    latest_ordinal: int
    source_reference: PassageReference | None = None


@dataclass(frozen=True, slots=True)
class ReportLedger:
    anchor: ReportLedgerAnchor
    history: ForecastLedger | IndicatorLedger
