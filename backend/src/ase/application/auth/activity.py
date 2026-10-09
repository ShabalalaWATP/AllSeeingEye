"""Explicit human activity and durable idle expiry at authentication transactions."""

from dataclasses import replace
from math import ceil
from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import RateLimited, SessionIdleExpired, Unauthenticated
from ase.domain.session_activity import SessionActivity


async def record_idle_expiry(
    tokens: RefreshTokenRepository,
    auditor: Auditor,
    user_id: UUID,
    family_id: UUID,
    activity: SessionActivity,
    context: RequestContext,
) -> None:
    # The caller owns the transaction. The revocation UPDATE claims the transition,
    # so repeated expired refreshes/heartbeats cannot duplicate the expiry audit.
    if await tokens.revoke_family(family_id, activity.server_now):
        await auditor.record(AuditAction.SESSION_IDLE_EXPIRED, actor=user_id, ip=context.ip)


class SessionActivityUseCase:
    def __init__(
        self,
        users: UserRepository,
        tokens: RefreshTokenRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users, self._tokens, self._clock = users, tokens, clock
        self._auditor, self._uow = auditor, uow

    async def execute(self, claims: AccessClaims, context: RequestContext) -> SessionActivity:
        # Share the account lock with refresh, MFA and account/security changes.
        # Activity is read again beneath the lock, never from a pre-lock token snapshot.
        await self._users.lock_by_id(claims.user_id)
        try:
            await validate_current_session(claims, self._users, self._tokens, self._clock)
        except SessionIdleExpired:
            activity = await self._tokens.activity(
                claims.user_id, claims.family_id, self._clock.now()
            )
            if activity is not None:
                await record_idle_expiry(
                    self._tokens, self._auditor, claims.user_id, claims.family_id, activity, context
                )
                await self._uow.commit()
            raise
        now = self._clock.now()
        activity = await self._tokens.activity(claims.user_id, claims.family_id, now)
        if activity is None:
            raise Unauthenticated()
        now = self._clock.now()
        activity = replace(activity, server_now=now)
        # Check after the awaited read too. An event at/after the deadline cannot revive it.
        if activity.expired:
            await record_idle_expiry(
                self._tokens, self._auditor, claims.user_id, claims.family_id, activity, context
            )
            await self._uow.commit()
            raise SessionIdleExpired(fields={"idle_minutes": str(activity.idle_minutes)})
        if not await self._tokens.touch_activity(claims.family_id, now):
            raise RateLimited(ceil(60 - (now - activity.last_activity_at).total_seconds()))
        activity = await self._tokens.activity(claims.user_id, claims.family_id, now)
        assert activity is not None  # noqa: S101
        await self._uow.commit()
        return activity
