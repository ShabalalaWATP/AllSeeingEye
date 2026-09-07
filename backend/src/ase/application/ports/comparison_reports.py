"""Bounded visible report inventory for exact comparison selection."""

from typing import Protocol

from ase.domain.access import Visibility
from ase.domain.report_records import ReportRecord


class ComparisonReportRepository(Protocol):
    async def page(
        self, visibility: Visibility, query: str, limit: int, offset: int
    ) -> tuple[list[ReportRecord], int]: ...
