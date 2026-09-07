"""Explicit transient output of report and automatic-claim production."""

from dataclasses import dataclass

from ase.application.reports.automatic_claims import PendingAutomaticClaims
from ase.domain.report_records import ReportVersion


@dataclass(frozen=True, slots=True)
class ProductionResult:
    version: ReportVersion
    claims: PendingAutomaticClaims | None = None
