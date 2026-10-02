"""Bounded offline STIX rendering; HTTP release uses the exact-version fence."""

import asyncio
from threading import BoundedSemaphore
from uuid import UUID

from ase.application.ports.stix import StixRenderer
from ase.application.reports.access import GetReportUseCase
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.report_documents import ReportFile
from ase.domain.stix import StixTlp
from ase.domain.users import User

_SLOTS = BoundedSemaphore(2)


class ExportStix:
    def __init__(self, reader: GetReportUseCase, renderer: StixRenderer) -> None:
        self._reader, self._renderer = reader, renderer

    async def execute(self, actor: User, report_id: UUID, number: int, tlp: StixTlp) -> ReportFile:
        if number < 1:
            raise InvalidRequest("Select an exact report version.")
        record, version = await self._reader.execute(actor, report_id, number)
        if not _SLOTS.acquire(blocking=False):
            raise RateLimited(5)

        def render() -> bytes:
            try:
                return self._renderer.render(record, version, tlp)
            finally:
                _SLOTS.release()

        task = asyncio.create_task(asyncio.to_thread(render))
        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        content = await asyncio.shield(task)
        return ReportFile(
            content,
            "application/stix+json",
            f"report-{report_id}-v{number}.stix.json",
            version.id,
            version.number,
        )
