"""Refresh with rotation and family reuse detection, plus logout."""

from __future__ import annotations

from datetime import datetime
from typing import NoReturn

from ase.application.auditing import Auditor
from ase.application.auth.sessions import SessionFactory
from ase.application.dto import AuthSession, RequestContext
from ase.application.ports import (
    Clock,
    RefreshTokenRepository,
    TokenGenerator,
    UnitOfWork,
    UserRepository,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRefreshToken
from ase.domain.tokens import RefreshToken


class RefreshUseCase:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        generator: TokenGenerator,
        sessions: SessionFactory,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._generator = generator
        self._sessions = sessions
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(self, refresh_secret: str | None, context: RequestContext) -> AuthSession:
        if not refresh_secret:
            raise InvalidRefreshToken()
        token = await self._refresh_tokens.get_by_hash(self._generator.hash(refresh_secret))
        if token is None:
            raise InvalidRefreshToken()
        now = self._clock.now()
        if token.revoked_at is not None:
            await self._reject_reuse(token, now, context)
        if not token.is_valid(now):
            raise InvalidRefreshToken()
        user = await self._users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshToken()
        # A stale read must never issue a second child. The claim and child creation
        # commit together; a competing claim waits and then fails against the DB state.
        if not await self._refresh_tokens.consume(token.id, now):
            await self._reject_reuse(token, now, context)
        session = await self._sessions.start(
            user, context, family_id=token.family_id, parent_id=token.id
        )
        await self._auditor.record(AuditAction.TOKEN_REFRESHED, actor=user.id, ip=context.ip)
        await self._uow.commit()
        return session

    async def _reject_reuse(
        self,
        token: RefreshToken,
        now: datetime,
        context: RequestContext,
    ) -> NoReturn:
        await self._refresh_tokens.revoke_family(token.family_id, now)
        await self._auditor.record(
            AuditAction.REFRESH_REUSE_DETECTED,
            actor=token.user_id,
            ip=context.ip,
            details={"family_id": str(token.family_id)},
        )
        await self._uow.commit()
        raise InvalidRefreshToken()


class LogoutUseCase:
    def __init__(
        self,
        refresh_tokens: RefreshTokenRepository,
        generator: TokenGenerator,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._refresh_tokens = refresh_tokens
        self._generator = generator
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(self, refresh_secret: str | None, context: RequestContext) -> None:
        if not refresh_secret:
            return
        token = await self._refresh_tokens.get_by_hash(self._generator.hash(refresh_secret))
        if token is None:
            return
        await self._refresh_tokens.revoke_family(token.family_id, self._clock.now())
        await self._auditor.record(AuditAction.LOGOUT, actor=token.user_id, ip=context.ip)
        await self._uow.commit()
