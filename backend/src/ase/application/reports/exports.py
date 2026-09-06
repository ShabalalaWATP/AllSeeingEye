"""Authorised export and comparison use cases, sharing the report reader's access rules."""

from __future__ import annotations

import asyncio
from uuid import UUID

from ase.application.ports.report_export import ReportRenderer
from ase.application.reports.access import GetReportUseCase
from ase.application.reports.comparison import compare_versions
from ase.application.reports.document import build_document
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import ExportFormat, ReportComparison, ReportFile
from ase.domain.users import User

MEDIA_TYPES = {
    ExportFormat.PDF: "application/pdf",
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class ExportReportUseCase:
    def __init__(self, reader: GetReportUseCase, renderer: ReportRenderer) -> None:
        self._reader = reader
        self._renderer = renderer

    async def execute(
        self, actor: User, report_id: UUID, format: ExportFormat, number: int | None = None
    ) -> ReportFile:
        if number is not None and number < 1:
            raise InvalidRequest("A report version must be positive.")
        record, version = await self._reader.execute(actor, report_id, number)
        document = build_document(record, version)
        content = await asyncio.to_thread(self._renderer.render, document, format)
        await self._reader.recheck(actor, report_id, version.number)
        return ReportFile(
            content, MEDIA_TYPES[format], f"report-{report_id}-v{version.number}.{format.value}"
        )


class CompareReportsUseCase:
    def __init__(self, reader: GetReportUseCase) -> None:
        self._reader = reader

    async def execute(
        self, actor: User, report_id: UUID, from_version: int, to_version: int
    ) -> ReportComparison:
        if from_version < 1 or to_version < 1:
            raise InvalidRequest("Report versions must be positive.")
        record, before = await self._reader.execute(actor, report_id, from_version)
        _, after = await self._reader.execute(actor, report_id, to_version)
        return compare_versions(record, before, after)
