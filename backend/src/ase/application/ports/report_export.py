"""Offline renderer boundary. Renderers receive bounded plain text, never live URLs."""

from typing import Protocol

from ase.domain.report_documents import ExportFormat, ReportDocument


class ReportRenderer(Protocol):
    def render(self, document: ReportDocument, format: ExportFormat) -> bytes: ...
