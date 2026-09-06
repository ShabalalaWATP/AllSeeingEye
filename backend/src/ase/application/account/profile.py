"""Self-service defaults, restricted to the current active identity."""

from dataclasses import replace
from typing import Any

from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.profile import ProfileRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest
from ase.domain.profile import PersonalProfile


class ProfileUseCase:
    def __init__(
        self,
        users: UserRepository,
        profiles: ProfileRepository,
        auditor: Auditor,
        uow: UnitOfWork,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
    ) -> None:
        self._users = users
        self._profiles = profiles
        self._auditor = auditor
        self._uow = uow
        self._refresh_tokens = refresh_tokens
        self._clock = clock

    async def get(self, claims: AccessClaims) -> PersonalProfile:
        current = await validate_current_session(
            claims, self._users, self._refresh_tokens, self._clock
        )
        profile = await self._profiles.get(current.id, current.display_name)
        await validate_current_session(claims, self._users, self._refresh_tokens, self._clock)
        return profile

    async def update(
        self,
        claims: AccessClaims,
        changes: dict[str, Any],
        context: RequestContext,
    ) -> PersonalProfile:
        # Follow administrative lock ordering before reloading identity. A profile
        # save must never overwrite a concurrent role, credential or status change.
        await self._users.lock_administration()
        await self._users.lock_by_id(claims.user_id)
        # A selected-session revocation does not change security_version. Verify
        # the actual family after acquiring the same locks as session management.
        current = await validate_current_session(
            claims, self._users, self._refresh_tokens, self._clock
        )
        previous = await self._profiles.get(current.id, current.display_name)
        try:
            profile = replace(previous, **changes)
        except (TypeError, ValueError) as exc:
            raise InvalidRequest("Invalid personal profile preferences") from exc
        current.display_name = profile.display_name
        await self._users.save(current)
        await self._profiles.save(current.id, profile)
        await self._auditor.record(
            AuditAction.USER_UPDATED,
            actor=current.id,
            subject=str(current.id),
            ip=context.ip,
            details={"profile_fields": sorted(changes)},
        )
        await self._uow.commit()
        return profile
