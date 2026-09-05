"""Persistence port for reports and their versions."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ase.domain.report_records import ReportRecord, ReportVersion


class ReportRepository(Protocol):
    async def add(self, record: ReportRecord, version: ReportVersion) -> None: ...
    async def add_version(self, record: ReportRecord, version: ReportVersion) -> None:
        """Store a further version and the record's updated status and latest number."""
        ...

    async def get(self, report_id: UUID) -> ReportRecord | None: ...
    async def get_version(self, report_id: UUID, number: int) -> ReportVersion | None: ...
    async def list_recent(self, limit: int) -> list[ReportRecord]: ...
    async def delete(self, report_id: UUID) -> None: ...
