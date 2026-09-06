"""Offline packaging boundary. Implementations must not fetch evidence URLs."""

from typing import Protocol

from ase.domain.report_records import ReportRecord, ReportVersion


class EvidencePackageRenderer(Protocol):
    def render(self, record: ReportRecord, version: ReportVersion) -> bytes: ...
