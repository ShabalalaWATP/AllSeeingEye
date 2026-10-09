"""Refresh with rotation and family reuse detection, plus logout."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import NoReturn
from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.auth.activity import record_idle_expiry
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
from ase.domain.errors import InvalidRefreshToken, SessionIdleExpired
from ase.domain.session_activity import SessionActivity
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

    async def execute(
        self, refresh_secret: str | None, context: RequestContext, *, activity_signal: bool = False
    ) -> AuthSession:
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
        user = await self._users.lock_by_id(token.user_id)
        now = self._clock.now()
        if user is None or not user.is_active or (user.is_admin and not token.mfa_verified):
            raise InvalidRefreshToken()
        if not token.is_valid(now):
            raise InvalidRefreshToken()
        activity = await self._refresh_tokens.activity(user.id, token.family_id, now)
        if activity is None:
            raise InvalidRefreshToken()
        now = self._clock.now()
        activity = replace(activity, server_now=now)
        if activity.expired:
            await record_idle_expiry(
                self._refresh_tokens, self._auditor, user.id, token.family_id, activity, context
            )
            await self._uow.commit()
            raise SessionIdleExpired(fields={"idle_minutes": str(activity.idle_minutes)})
        if not await self._refresh_tokens.family_is_active(
            user.id, token.family_id, now, require_mfa=user.is_admin
        ):
            await self._reject_reuse(token, now, context)
        if activity_signal:
            # The same persistent minute budget applies to refresh and explicit heartbeat.
            await self._refresh_tokens.touch_activity(token.family_id, now)
        # A stale read must never issue a second child. The claim and child creation
        # commit together; a competing claim waits and then fails against the DB state.
        if not await self._refresh_tokens.consume(token.id, now):
            await self._reject_reuse(token, now, context)
        session = await self._sessions.start(
            user,
            context,
            family_id=token.family_id,
            parent_id=token.id,
            mfa_verified=token.mfa_verified,
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
        )
        await self._uow.commit()
        raise InvalidRefreshToken()


class LogoutUseCase:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        generator: TokenGenerator,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._generator = generator
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self,
        refresh_secret: str | None,
        context: RequestContext,
        *,
        expected_family: UUID | None = None,
        idle_only: bool = False,
    ) -> bool | SessionActivity:
        if idle_only and expected_family is None:
            # Conditional expiry must never inspect or mutate an unbound replacement.
            return False
        if not refresh_secret:
            return True
        token = await self._refresh_tokens.get_by_hash(self._generator.hash(refresh_secret))
        if token is None:
            return True
        if expected_family is not None and token.family_id != expected_family:
            return False
        user = await self._users.lock_by_id(token.user_id)
        now = self._clock.now()
        activity = await self._refresh_tokens.activity(token.user_id, token.family_id, now)
        if activity is not None:
            activity = replace(activity, server_now=self._clock.now())
        if (
            idle_only
            and activity is not None
            and not activity.expired
            and user is not None
            and user.is_active
            and await self._refresh_tokens.family_is_active(
                user.id, token.family_id, activity.server_now, require_mfa=user.is_admin
            )
        ):
            # A suspended tab can miss another tab's accepted activity. Return the
            # authoritative deadline without touching activity, tokens or cookies.
            return activity
        if activity is not None and activity.expired:
            await record_idle_expiry(
                self._refresh_tokens,
                self._auditor,
                token.user_id,
                token.family_id,
                activity,
                context,
            )
        else:
            await self._refresh_tokens.revoke_family(token.family_id, now)
            await self._auditor.record(AuditAction.LOGOUT, actor=token.user_id, ip=context.ip)
        await self._uow.commit()
        return True
