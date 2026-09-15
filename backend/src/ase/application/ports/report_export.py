"""Offline renderer boundary. Renderers receive bounded plain text, never live URLs."""

from typing import Protocol

from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import ExportFormat, ReportDocument
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.source_review_records import SourceReviewSnapshot


class ReportRenderer(Protocol):
    def render(self, document: ReportDocument, format: ExportFormat) -> bytes: ...


class AsyncReportRenderer(Protocol):
    async def render(self, document: ReportDocument, format: ExportFormat) -> bytes: ...


class AsyncReportProjector(Protocol):
    async def build(
        self,
        record: ReportRecord,
        version: ReportVersion,
        reviewed_snapshot: SourceReviewSnapshot | None = None,
    ) -> ReportDocument: ...


class RenderCleanupFailed(InvalidRequest):
    """Descendant termination is unverified; admission must remain quarantined."""
