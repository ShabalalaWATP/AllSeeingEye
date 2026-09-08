"""Awaitable export admission, retaining capacity until all work has stopped."""

import asyncio
import threading
from typing import Protocol

from ase.adapters.reports.documents import ReportDocumentRenderer
from ase.application.ports.report_export import RenderCleanupFailed, ReportRenderer
from ase.domain.errors import RateLimited
from ase.domain.report_documents import ExportFormat, ReportDocument

_SLOTS = threading.BoundedSemaphore(2)


class PdfWorker(Protocol):
    async def render(self, document: ReportDocument) -> bytes: ...


async def settle(task: asyncio.Task[bytes]) -> bytes:
    """Do not release admission while cancellation leaves a renderer running."""
    cancelled = False
    try:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise
                cancelled = True
    finally:
        if cancelled:
            raise asyncio.CancelledError


class AsyncReportDocumentRenderer:
    def __init__(
        self, *, worker: PdfWorker | None = None, legacy: ReportRenderer | None = None
    ) -> None:
        self.worker = worker
        self.legacy = legacy or ReportDocumentRenderer()

    async def render(self, document: ReportDocument, format: ExportFormat) -> bytes:
        if not _SLOTS.acquire(blocking=False):
            raise RateLimited(5)
        release = True
        try:
            if (
                self.worker is not None
                and format is ExportFormat.PDF
                and document.language in {"ar", "fa"}
            ):
                # The worker owns cancellation, deadline and descendant cleanup.
                return await self.worker.render(document)
            return await settle(
                asyncio.create_task(asyncio.to_thread(self.legacy.render, document, format))
            )
        except RenderCleanupFailed:
            release = False
            raise
        finally:
            if release:
                _SLOTS.release()
