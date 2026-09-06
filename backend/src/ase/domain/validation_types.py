"""Results of mechanical report validation, shared by focused validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ase.domain.reports import ReportBody


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    severity: Severity
    location: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    body: ReportBody
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def passed(self) -> bool:
        return not self.errors
