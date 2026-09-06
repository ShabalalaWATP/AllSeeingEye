"""Resolve one authorised frozen version and recheck access after packaging."""

import asyncio
from threading import BoundedSemaphore
from uuid import UUID

from ase.application.ports.evidence_package import EvidencePackageRenderer
from ase.application.reports.access import GetReportUseCase
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.report_documents import ReportFile
from ase.domain.users import User

_PACKAGE_SLOTS = BoundedSemaphore(2)


class ExportEvidencePackage:
    def __init__(self, reader: GetReportUseCase, renderer: EvidencePackageRenderer) -> None:
        self._reader = reader
        self._renderer = renderer

    async def execute(self, actor: User, report_id: UUID, number: int | None = None) -> ReportFile:
        if number is not None and number < 1:
            raise InvalidRequest("A report version must be positive.")
        record, version = await self._reader.execute(actor, report_id, number)
        if not _PACKAGE_SLOTS.acquire(blocking=False):
            raise RateLimited(5)

        def render() -> bytes:
            try:
                return self._renderer.render(record, version)
            finally:
                _PACKAGE_SLOTS.release()

        # Cancelling the request cannot stop a running compression thread. Keep its
        # slot until the worker finishes, including when cancellation precedes start.
        task = asyncio.create_task(asyncio.to_thread(render))
        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        content = await asyncio.shield(task)
        await self._reader.recheck(actor, report_id, version.number)
        return ReportFile(content, "application/zip", f"evidence-{report_id}-v{version.number}.zip")
