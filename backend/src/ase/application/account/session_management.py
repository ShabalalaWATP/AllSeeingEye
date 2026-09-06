"""Own-session controls, serialised with credential changes and refresh rotation."""

from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.account_sessions import AccountSessionRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import NotFound
from ase.domain.session_summary import SessionPage


class AccountSessionManagement:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        sessions: AccountSessionRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._refresh = refresh_tokens
        self._sessions = sessions
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def _validate(self, claims: AccessClaims) -> None:
        await self._users.lock_administration()
        await self._users.lock_by_id(claims.user_id)
        await validate_current_session(claims, self._users, self._refresh, self._clock)

    async def list(self, claims: AccessClaims) -> SessionPage:
        await self._validate(claims)
        result = await self._sessions.list_active(
            claims.user_id, claims.family_id, self._clock.now()
        )
        await self._uow.commit()
        return result

    async def revoke(
        self,
        claims: AccessClaims,
        family_id: UUID,
        context: RequestContext,
    ) -> None:
        await self._validate(claims)
        if not await self._sessions.owns_family(claims.user_id, family_id):
            raise NotFound()
        await self._refresh.revoke_family(family_id, self._clock.now())
        await self._auditor.record(
            AuditAction.LOGOUT,
            actor=claims.user_id,
            ip=context.ip,
            details={"scope": "selected_session"},
        )
        await self._uow.commit()

    async def revoke_others(self, claims: AccessClaims, context: RequestContext) -> None:
        await self._validate(claims)
        await self._sessions.revoke_others(claims.user_id, claims.family_id, self._clock.now())
        await self._auditor.record(
            AuditAction.LOGOUT,
            actor=claims.user_id,
            ip=context.ip,
            details={"scope": "other_sessions"},
        )
        await self._uow.commit()
