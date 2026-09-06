"""Report access consistently applies personal and current team membership boundaries."""

from __future__ import annotations

from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import UnitOfWork
from ase.application.ports.reports import ReportRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import NotFound
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.users import User

MAX_LIST = 200


class ListReportsUseCase:
    def __init__(self, reports: ReportRepository, access: AccessPolicy) -> None:
        self._reports = reports
        self._access = access

    async def execute(self, actor: User, limit: int = 50) -> list[ReportRecord]:
        access = await self._access.context(actor)
        return await self._reports.list_visible(access.visibility, min(max(1, limit), MAX_LIST))


class GetReportUseCase:
    def __init__(self, reports: ReportRepository, access: AccessPolicy, uow: UnitOfWork) -> None:
        self._reports = reports
        self._access = access
        self._uow = uow

    async def recheck(self, actor: User, report_id: UUID, number: int) -> None:
        """End a renderer's read snapshot and authorise again before releasing private bytes."""
        await self._uow.rollback()
        await self.execute(actor, report_id, number)

    async def execute(
        self, actor: User, report_id: UUID, number: int | None = None
    ) -> tuple[ReportRecord, ReportVersion]:
        access = await self._access.context(actor)
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        access.require_read(record.created_by, record.team_id)
        version = await self._reports.get_version(report_id, number or record.latest_version)
        if version is None:
            raise NotFound()
        return record, version


class DeleteReportUseCase:
    def __init__(
        self, reports: ReportRepository, auditor: Auditor, uow: UnitOfWork, access: AccessPolicy
    ) -> None:
        self._reports = reports
        self._auditor = auditor
        self._uow = uow
        self._access = access

    async def execute(self, actor: User, report_id: UUID, context: RequestContext) -> None:
        access = await self._access.context(actor, for_update=True)
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        access.require_write(record.created_by, record.team_id)
        await self._reports.delete(report_id)
        await self._auditor.record(
            AuditAction.REPORT_DELETED,
            actor=actor.id,
            subject=str(report_id),
            ip=context.ip,
            details={"template": record.template, "title": record.title},
        )
        await self._uow.commit()
