"""Owner controls and privacy-aware discovery for operator directory profiles."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sqlalchemy.exc import IntegrityError

from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import (
    Clock,
    RateLimiter,
    RefreshTokenRepository,
    UnitOfWork,
    UserRepository,
)
from ase.application.ports.directory_profile import DirectoryProfileRepository
from ase.domain.audit import AuditAction
from ase.domain.directory_profile import DirectoryPage, DirectoryProfile
from ase.domain.errors import Conflict, InvalidRequest, RateLimited, UsernameTaken
from ase.domain.users import User


class DirectoryProfileUseCase:
    """Keep public discovery fields isolated from private account preferences."""

    def __init__(
        self,
        users: UserRepository,
        profiles: DirectoryProfileRepository,
        auditor: Auditor,
        uow: UnitOfWork,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
        limiter: RateLimiter,
    ) -> None:
        self._users = users
        self._profiles = profiles
        self._auditor = auditor
        self._uow = uow
        self._refresh_tokens = refresh_tokens
        self._clock = clock
        self._limiter = limiter

    async def get(self, claims: AccessClaims) -> DirectoryProfile:
        current = await validate_current_session(
            claims, self._users, self._refresh_tokens, self._clock
        )
        profile = await self._profiles.get(current.id)
        # A newly registered account has no row until it edits the directory profile.
        return profile or DirectoryProfile(user_id=current.id)

    async def update(
        self,
        claims: AccessClaims,
        changes: dict[str, Any],
        expected_revision: int | None,
        context: RequestContext,
    ) -> DirectoryProfile:
        # Match administrative/session mutation ordering so a revoked or deactivated
        # account cannot persist a profile after its identity has changed.
        await self._users.lock_administration()
        await self._users.lock_by_id(claims.user_id)
        current = await validate_current_session(
            claims, self._users, self._refresh_tokens, self._clock
        )
        previous = await self._profiles.get(current.id) or DirectoryProfile(user_id=current.id)
        if expected_revision is not None and expected_revision != previous.revision:
            raise Conflict("The directory profile changed. Reload it before saving again.")
        try:
            profile = replace(
                previous,
                **changes,
                revision=previous.revision + 1,
                updated_at=self._clock.now(),
            )
        except (TypeError, ValueError) as exc:
            raise InvalidRequest("Invalid directory profile") from exc
        try:
            await self._profiles.save(profile)
        except IntegrityError as exc:
            await self._uow.rollback()
            # Do not surface database constraint text, which can disclose schema details.
            if "username" in str(exc.orig).lower():
                raise UsernameTaken() from None
            raise
        await self._auditor.record(
            AuditAction.DIRECTORY_PROFILE_UPDATED,
            actor=current.id,
            subject=str(current.id),
            ip=context.ip,
            details={"profile_fields": sorted(changes)},
        )
        await self._uow.commit()
        return profile

    async def search(self, actor: User, query: str, limit: int, offset: int) -> DirectoryPage:
        if not 1 <= limit <= 20 or not 0 <= offset <= 1000:
            raise InvalidRequest("Invalid directory page bounds")
        query = " ".join(query.split())
        if len(query) < 2:
            raise InvalidRequest("Directory search must contain at least two characters")
        retry_after = self._limiter.hit(f"directory-search:{actor.id}", 30, 60)
        if retry_after is not None:
            raise RateLimited(retry_after)
        return await self._profiles.search(query, limit, offset)
