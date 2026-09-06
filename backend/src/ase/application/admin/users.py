"""User administration: list, update role or active flag, issue reset links."""

from __future__ import annotations

from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext, ResetLinkResult
from ase.application.policy import forbid_self_modification, require_admin
from ase.application.ports import (
    Clock,
    LinkBuilder,
    PasswordTokenRepository,
    RefreshTokenRepository,
    TokenGenerator,
    UnitOfWork,
    UserRepository,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, NotFound, UserInactive
from ase.domain.tokens import PasswordToken, TokenPurpose, ttl_for
from ase.domain.users import Role, User


async def _lock_accounts(users: UserRepository, actor: User, target_id: UUID) -> User:
    """Global guard, ordered account locks, then authoritative actor authorisation."""
    require_admin(actor)
    await users.lock_administration()
    locked = {}
    for identity in sorted({actor.id, target_id}):
        locked[identity] = await users.lock_by_id(identity)
    current_actor = locked[actor.id]
    if (
        current_actor is None
        or not current_actor.is_active
        or current_actor.security_version != actor.security_version
    ):
        raise Forbidden()
    require_admin(current_actor)
    target = locked[target_id]
    if target is None:
        raise NotFound()
    return target


class ListUsersUseCase:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, actor: User) -> list[User]:
        require_admin(actor)
        return await self._users.list_all()


class UpdateUserUseCase:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        password_tokens: PasswordTokenRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._password_tokens = password_tokens
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self,
        actor: User,
        user_id: UUID,
        role: Role | None,
        is_active: bool | None,
        context: RequestContext,
    ) -> User:
        require_admin(actor)
        forbid_self_modification(actor, user_id)
        # Self-modification is forbidden and the serialised actor must remain an
        # active admin, so changing another account always leaves that admin.
        user = await _lock_accounts(self._users, actor, user_id)
        changes: dict[str, object] = {}
        if role is not None and role is not user.role:
            user.role = role
            changes["role"] = role.value
        if is_active is not None and is_active != user.is_active:
            user.is_active = is_active
            changes["is_active"] = is_active
        if changes:
            user.security_version += 1
            # A demotion or deactivation must end every live session.
            now = self._clock.now()
            await self._refresh_tokens.revoke_all_for_user(user.id, now)
            if user.is_active is False:
                # And no outstanding activation or reset link may bring the account back.
                await self._password_tokens.revoke_all_for_user(user.id, now)
        await self._users.save(user)
        await self._auditor.record(
            AuditAction.USER_UPDATED,
            actor=actor.id,
            subject=user.email,
            ip=context.ip,
            details=changes,
        )
        await self._uow.commit()
        return user


class IssueResetLinkUseCase:
    def __init__(
        self,
        users: UserRepository,
        password_tokens: PasswordTokenRepository,
        generator: TokenGenerator,
        links: LinkBuilder,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._password_tokens = password_tokens
        self._generator = generator
        self._links = links
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(self, actor: User, user_id: UUID, context: RequestContext) -> ResetLinkResult:
        user = await _lock_accounts(self._users, actor, user_id)
        if not user.is_active:
            raise UserInactive()
        now = self._clock.now()
        secret = self._generator.new_secret()
        expires_at = now + ttl_for(TokenPurpose.RESET)
        await self._password_tokens.add(
            PasswordToken(
                id=uuid4(),
                user_id=user.id,
                token_hash=self._generator.hash(secret),
                purpose=TokenPurpose.RESET,
                expires_at=expires_at,
                used_at=None,
                created_at=now,
            )
        )
        await self._auditor.record(
            AuditAction.RESET_LINK_ISSUED, actor=actor.id, subject=user.email, ip=context.ip
        )
        await self._uow.commit()
        return ResetLinkResult(
            reset_link=self._links.link_for(TokenPurpose.RESET, secret), expires_at=expires_at
        )
