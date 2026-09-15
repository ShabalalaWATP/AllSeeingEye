"""Owner avatar uploads and roster/directory-scoped avatar reads."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

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
from ase.application.ports.directory_profile import AvatarProcessor, DirectoryProfileRepository
from ase.domain.audit import AuditAction
from ase.domain.directory_avatar import MAX_AVATAR_UPLOAD_BYTES, DirectoryAvatar
from ase.domain.directory_profile import DirectoryProfile
from ase.domain.errors import InvalidRequest, NotFound, RateLimited
from ase.domain.users import User

UPLOADS_PER_WINDOW = 10
UPLOAD_WINDOW_SECONDS = 600


class DirectoryAvatarUseCase:
    """Avatars follow display-name visibility: shared team rosters and the opt-in directory."""

    def __init__(
        self,
        users: UserRepository,
        profiles: DirectoryProfileRepository,
        processor: AvatarProcessor,
        auditor: Auditor,
        uow: UnitOfWork,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
        limiter: RateLimiter,
    ) -> None:
        self._users = users
        self._profiles = profiles
        self._processor = processor
        self._auditor = auditor
        self._uow = uow
        self._refresh_tokens = refresh_tokens
        self._clock = clock
        self._limiter = limiter

    async def _locked_owner(self, claims: AccessClaims) -> tuple[User, DirectoryProfile]:
        await self._users.lock_administration()
        await self._users.lock_by_id(claims.user_id)
        current = await validate_current_session(
            claims, self._users, self._refresh_tokens, self._clock
        )
        profile = await self._profiles.get(current.id) or DirectoryProfile(user_id=current.id)
        return current, profile

    async def upload(
        self, claims: AccessClaims, data: bytes, context: RequestContext
    ) -> DirectoryProfile:
        if len(data) > MAX_AVATAR_UPLOAD_BYTES:
            raise InvalidRequest("Avatar images must be 2 MB or smaller.")
        current = await validate_current_session(
            claims, self._users, self._refresh_tokens, self._clock
        )
        retry_after = self._limiter.hit(
            f"directory-avatar:{current.id}", UPLOADS_PER_WINDOW, UPLOAD_WINDOW_SECONDS
        )
        if retry_after is not None:
            raise RateLimited(retry_after)
        # Close the read transaction before CPU-bound decoding; no lock is held meanwhile.
        await self._uow.rollback()
        image = await self._processor.process(data)
        current, previous = await self._locked_owner(claims)
        now = self._clock.now()
        profile = replace(
            previous,
            avatar_sha256=image.sha256,
            revision=previous.revision + 1,
            updated_at=now,
        )
        await self._profiles.save(profile)
        await self._profiles.save_avatar(DirectoryAvatar(current.id, image, now))
        await self._auditor.record(
            AuditAction.DIRECTORY_AVATAR_UPDATED,
            actor=current.id,
            subject=str(current.id),
            ip=context.ip,
            details={"byte_count": len(image.content), "content_type": image.content_type},
        )
        await self._uow.commit()
        return profile

    async def remove(self, claims: AccessClaims, context: RequestContext) -> DirectoryProfile:
        current, previous = await self._locked_owner(claims)
        if previous.avatar_sha256 is None:
            await self._uow.rollback()
            return previous
        profile = replace(
            previous,
            avatar_sha256=None,
            revision=previous.revision + 1,
            updated_at=self._clock.now(),
        )
        await self._profiles.save(profile)
        await self._profiles.delete_avatar(current.id)
        await self._auditor.record(
            AuditAction.DIRECTORY_AVATAR_REMOVED,
            actor=current.id,
            subject=str(current.id),
            ip=context.ip,
        )
        await self._uow.commit()
        return profile

    async def read(self, viewer: User, target_id: UUID) -> DirectoryAvatar:
        """Return an avatar only where the viewer may already see the display name."""

        avatar = await self._profiles.get_avatar(target_id)
        if avatar is None:
            raise NotFound()
        if viewer.id == target_id or viewer.is_admin:
            return avatar
        profile = await self._profiles.get(target_id)
        target = await self._users.get_by_id(target_id)
        if profile is None or target is None:
            raise NotFound()
        if profile.is_discoverable and target.is_active and profile.username is not None:
            return avatar
        if await self._profiles.shares_team(viewer.id, target_id):
            return avatar
        # Inaccessible and absent avatars are indistinguishable.
        raise NotFound()
