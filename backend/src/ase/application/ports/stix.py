"""Offline STIX serialisation boundary over one frozen report version."""

from typing import Protocol

from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.stix import StixTlp


class StixRenderer(Protocol):
    def render(self, record: ReportRecord, version: ReportVersion, tlp: StixTlp) -> bytes: ...
