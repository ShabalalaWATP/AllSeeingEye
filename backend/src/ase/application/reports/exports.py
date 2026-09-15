"""Authorised export and comparison use cases, sharing the report reader's access rules."""

from __future__ import annotations

import asyncio
from uuid import UUID

from ase.application.ports.report_export import AsyncReportProjector, AsyncReportRenderer
from ase.application.reports.access import GetReportUseCase
from ase.application.reports.comparison import compare_versions
from ase.application.reports.document import build_document
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import ExportFormat, ReportComparison, ReportFile
from ase.domain.source_review_records import SourceReviewSnapshot
from ase.domain.users import User

MEDIA_TYPES = {
    ExportFormat.PDF: "application/pdf",
    ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class ExportReportUseCase:
    def __init__(
        self,
        reader: GetReportUseCase,
        renderer: AsyncReportRenderer,
        projector: AsyncReportProjector | None = None,
    ) -> None:
        self._reader = reader
        self._renderer = renderer
        self._projector = projector

    async def execute(
        self,
        actor: User,
        report_id: UUID,
        format: ExportFormat,
        number: int | None = None,
        reviewed_snapshot: SourceReviewSnapshot | None = None,
    ) -> ReportFile:
        if number is not None and number < 1:
            raise InvalidRequest("A report version must be positive.")
        record, version = await self._reader.execute(actor, report_id, number)
        if self._projector is not None:
            document = (
                await self._projector.build(record, version)
                if reviewed_snapshot is None
                else await self._projector.build(record, version, reviewed_snapshot)
            )
        else:
            document = await asyncio.to_thread(
                build_document, record, version, reviewed_snapshot=reviewed_snapshot
            )
        content = await self._renderer.render(document, format)
        await self._reader.recheck(actor, report_id, version.number)
        return ReportFile(
            content,
            MEDIA_TYPES[format],
            f"report-{report_id}-v{version.number}.{format.value}",
            version.id,
            version.number,
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
