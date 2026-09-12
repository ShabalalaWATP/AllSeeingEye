"""Bounded off-loop projection of frozen report records into reader documents."""

from functools import partial

from ase.adapters.reports.async_documents import run_bounded_thread
from ase.application.reports.document import build_document
from ase.domain.report_documents import ReportDocument
from ase.domain.report_records import ReportRecord, ReportVersion


class AsyncReportDocumentProjector:
    def __init__(self, *, wait_for_slot: bool = False) -> None:
        self._wait_for_slot = wait_for_slot

    async def build(self, record: ReportRecord, version: ReportVersion) -> ReportDocument:
        return await run_bounded_thread(
            partial(build_document, record, version), wait_for_slot=self._wait_for_slot
        )
