"""Review and erase enquiries under current privileged session authority."""

from datetime import datetime, timedelta
from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.policy import require_admin
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.enterprise_enquiries import AdminEnquiryRepository
from ase.domain.audit import AuditAction
from ase.domain.enterprise_enquiries import EnquiryStatus, EnterpriseEnquiry
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.users import User


class AdminEnquiries:
    def __init__(
        self,
        repository: AdminEnquiryRepository,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        retention_days: int,
    ) -> None:
        self.repository, self.users, self.refresh = repository, users, refresh
        self.clock, self.auditor, self.uow = clock, auditor, uow
        self.retention_days = retention_days

    def _cutoff(self) -> datetime:
        return self.clock.now() - timedelta(days=self.retention_days)

    async def list(
        self, actor: User, status: EnquiryStatus | None, limit: int, offset: int
    ) -> tuple[list[EnterpriseEnquiry], int]:
        require_admin(actor)
        if not 1 <= limit <= 100 or offset < 0:
            raise InvalidRequest("Use a page size between 1 and 100 and a non-negative offset.")
        return await self.repository.list(self._cutoff(), status, limit, offset)

    async def get(self, actor: User, enquiry_id: UUID) -> EnterpriseEnquiry:
        require_admin(actor)
        item = await self.repository.get(enquiry_id, self._cutoff())
        if item is None:
            raise NotFound()
        return item

    async def _guard(self, claims: AccessClaims) -> User:
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        require_admin(actor)
        return actor

    async def set_status(
        self, claims: AccessClaims, enquiry_id: UUID, status: EnquiryStatus
    ) -> EnterpriseEnquiry:
        actor = await self._guard(claims)
        await self.get(actor, enquiry_id)
        await self.repository.set_status(enquiry_id, status, self.clock.now())
        await self.auditor.record(
            AuditAction.ENQUIRY_STATUS_CHANGED, actor=actor.id, subject=str(enquiry_id)
        )
        result = await self.get(actor, enquiry_id)
        await validate_current_session(claims, self.users, self.refresh, self.clock)
        await self.uow.commit()
        return result

    async def delete(self, claims: AccessClaims, enquiry_id: UUID) -> None:
        actor = await self._guard(claims)
        await self.get(actor, enquiry_id)
        await self.repository.delete(enquiry_id)
        await self.auditor.record(
            AuditAction.ENQUIRY_DELETED, actor=actor.id, subject=str(enquiry_id)
        )
        await validate_current_session(claims, self.users, self.refresh, self.clock)
        await self.uow.commit()
