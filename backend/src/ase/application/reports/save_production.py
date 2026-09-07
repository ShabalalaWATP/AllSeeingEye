"""One final authorised transaction for a report, its usage and automatic claims."""

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import UnitOfWork
from ase.application.ports.claims import ClaimRepository
from ase.application.ports.reports import ReportRepository
from ase.application.reports.automatic_claim_storage import AutomaticClaimStorage
from ase.application.reports.production_result import ProductionResult
from ase.domain.audit import AuditAction
from ase.domain.report_records import ReportRecord
from ase.domain.users import User


class SaveProduction:
    def __init__(
        self,
        reports: ReportRepository,
        claims: ClaimRepository | None,
        access: AccessPolicy,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.reports, self.access, self.auditor, self.uow = reports, access, auditor, uow
        self.claims = AutomaticClaimStorage(claims, auditor) if claims is not None else None

    async def save(
        self,
        actor: User,
        record: ReportRecord,
        result: ProductionResult,
        context: RequestContext,
        *,
        creating: bool,
        automation: bool,
    ) -> None:
        try:
            access = (
                await self.access.background(actor.id, record.team_id, for_update=True)
                if automation
                else await self.access.context(actor, for_update=True)
            )
            access.require_write(record.created_by, record.team_id)
            pending = result.claims
            if pending is not None:
                if self.claims is None:
                    raise ValueError("Automatic claims require transactional storage")
                pending = await self.claims.admit(access, record, result.version, pending)
                result.version.claim_generation = pending.receipt
            if creating:
                await self.reports.add(record, result.version)
            else:
                await self.reports.add_version(record, result.version)
            if pending is not None and self.claims is not None:
                await self.claims.write(access, record, result.version, pending, context)
            await self.auditor.record(
                AuditAction.REPORT_GENERATED,
                actor=actor.id,
                subject=str(record.id),
                ip=context.ip,
                details={
                    "template": record.template,
                    "version": result.version.number,
                    "status": result.version.status.value,
                    "attempts": result.version.attempts,
                },
            )
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
