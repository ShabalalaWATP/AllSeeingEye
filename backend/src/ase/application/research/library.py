"""Personal organisation never changes report ownership, scope or frozen versions."""

from dataclasses import replace
from uuid import UUID

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.reports import ReportRepository
from ase.application.ports.research_library import ResearchLibraryRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.research_library import LibraryPage, LibraryPreference, normalise_tag


class ResearchLibrary:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        reports: ReportRepository,
        library: ResearchLibraryRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.reports, self.library = (
            users,
            refresh_tokens,
            reports,
            library,
        )
        self.access, self.clock, self.auditor, self.uow = access, clock, auditor, uow

    async def context(self, claims: AccessClaims) -> AccessContext:
        # Membership changes, report deletion and revocation use the same lock ordering.
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        return await self.access.context(actor)

    async def require_report(self, claims: AccessClaims, report_id: UUID) -> None:
        access = await self.context(claims)
        report = await self.reports.get(report_id)
        if report is None:
            raise NotFound()
        access.require_read(report.created_by, report.team_id)

    async def list(
        self,
        claims: AccessClaims,
        limit: int = 50,
        offset: int = 0,
        favourite_only: bool = False,
        tag: str | None = None,
    ) -> LibraryPage:
        if not 1 <= limit <= 100 or not 0 <= offset <= 10000:
            raise InvalidRequest("Invalid library page bounds")
        try:
            tag = normalise_tag(tag) if tag is not None else None
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        access = await self.context(claims)
        result = await self.library.list_visible(
            access.visibility, limit, offset, favourite_only, tag
        )
        await self.uow.commit()
        return result

    async def get(self, claims: AccessClaims, report_id: UUID) -> LibraryPreference:
        await self.require_report(claims, report_id)
        result = await self.library.get(claims.user_id, report_id)
        await self.uow.commit()
        return result

    async def save(
        self,
        claims: AccessClaims,
        report_id: UUID,
        value: LibraryPreference,
        context: RequestContext,
    ) -> LibraryPreference:
        await self.require_report(claims, report_id)
        value = replace(value, updated_at=self.clock.now())
        await self.library.save(claims.user_id, report_id, value)
        await self.auditor.record(
            AuditAction.LIBRARY_UPDATED,
            actor=claims.user_id,
            subject=str(report_id),
            ip=context.ip,
            details={"tag_count": len(value.tags), "favourite": value.favourite},
        )
        await self.uow.commit()
        return value

    async def remove(self, claims: AccessClaims, report_id: UUID, context: RequestContext) -> None:
        await self.require_report(claims, report_id)
        await self.library.remove(claims.user_id, report_id)
        await self.auditor.record(
            AuditAction.LIBRARY_REMOVED, actor=claims.user_id, subject=str(report_id), ip=context.ip
        )
        await self.uow.commit()
