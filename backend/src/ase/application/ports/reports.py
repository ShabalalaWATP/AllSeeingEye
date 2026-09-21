"""Port for persisted reports: records, their versions and the frozen evidence they carry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.reports import ReportOrigin


class ReportRepository(Protocol):
    async def add(self, record: ReportRecord, version: ReportVersion) -> None: ...
    async def add_version(self, record: ReportRecord, version: ReportVersion) -> None: ...
    async def get(self, report_id: UUID) -> ReportRecord | None: ...
    async def get_version(self, report_id: UUID, number: int) -> ReportVersion | None: ...

    async def set_archives(
        self, version_id: UUID, archives: Mapping[str, str], markdown: str
    ) -> None:
        """Record archive addresses on a version's evidence (by label) and its re-rendered text."""
        ...

    async def list_recent(self, limit: int) -> list[ReportRecord]: ...
    async def list_visible(
        self,
        visibility: Visibility,
        limit: int,
        *,
        origin: ReportOrigin | None = None,
        offset: int = 0,
    ) -> list[ReportRecord]: ...
    async def delete(self, report_id: UUID) -> None: ...
