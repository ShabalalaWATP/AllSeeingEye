"""Reading, listing and deleting reports: anyone signed in reads; owners and admins delete."""

from __future__ import annotations

from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import UnitOfWork
from ase.application.ports.reports import ReportRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, NotFound
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.users import User

MAX_LIST = 200


class ListReportsUseCase:
    def __init__(self, reports: ReportRepository) -> None:
        self._reports = reports

    async def execute(self, actor: User, limit: int = 50) -> list[ReportRecord]:
        return await self._reports.list_recent(min(max(1, limit), MAX_LIST))


class GetReportUseCase:
    def __init__(self, reports: ReportRepository) -> None:
        self._reports = reports

    async def execute(
        self, actor: User, report_id: UUID, number: int | None = None
    ) -> tuple[ReportRecord, ReportVersion]:
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        version = await self._reports.get_version(report_id, number or record.latest_version)
        if version is None:
            raise NotFound()
        return record, version


class DeleteReportUseCase:
    def __init__(self, reports: ReportRepository, auditor: Auditor, uow: UnitOfWork) -> None:
        self._reports = reports
        self._auditor = auditor
        self._uow = uow

    async def execute(self, actor: User, report_id: UUID, context: RequestContext) -> None:
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        if record.created_by != actor.id and not actor.is_admin:
            raise Forbidden()
        await self._reports.delete(report_id)
        await self._auditor.record(
            AuditAction.REPORT_DELETED,
            actor=actor.id,
            subject=str(report_id),
            ip=context.ip,
            details={"template": record.template, "title": record.title},
        )
        await self._uow.commit()
