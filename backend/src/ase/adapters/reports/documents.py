"""PDF and DOCX exports without HTML, external relationships or network resources."""

from __future__ import annotations

import threading

from ase.adapters.reports.pdf import render_pdf
from ase.adapters.reports.word import render_docx
from ase.domain.errors import RateLimited
from ase.domain.report_documents import ExportFormat, ReportDocument

_RENDER_SLOTS = threading.BoundedSemaphore(2)


class ReportDocumentRenderer:
    def render(self, document: ReportDocument, format: ExportFormat) -> bytes:
        # CPU work runs off the event loop. Refuse excess requests instead of queuing
        # unbounded document jobs on a hobby-scale host.
        if not _RENDER_SLOTS.acquire(blocking=False):
            raise RateLimited(5)
        try:
            return render_pdf(document) if format is ExportFormat.PDF else render_docx(document)
        finally:
            _RENDER_SLOTS.release()
