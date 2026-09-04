"""Set a password from a single-use activation or reset token."""

from __future__ import annotations

from ase.application.auditing import Auditor
from ase.application.dto import RateLimits, RequestContext
from ase.application.ports import (
    Clock,
    PasswordHasher,
    PasswordTokenRepository,
    RateLimiter,
    RefreshTokenRepository,
    TokenGenerator,
    UnitOfWork,
    UserRepository,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidToken, RateLimited
from ase.domain.password_policy import validate_password
from ase.domain.tokens import TokenPurpose


class SetPasswordUseCase:
    def __init__(
        self,
        users: UserRepository,
        password_tokens: PasswordTokenRepository,
        refresh_tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        generator: TokenGenerator,
        clock: Clock,
        limiter: RateLimiter,
        limits: RateLimits,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._password_tokens = password_tokens
        self._refresh_tokens = refresh_tokens
        self._hasher = hasher
        self._generator = generator
        self._clock = clock
        self._limiter = limiter
        self._limits = limits
        self._auditor = auditor
        self._uow = uow

    async def execute(self, secret: str, new_password: str, context: RequestContext) -> None:
        retry_after = self._limiter.hit(
            f"set-password:ip:{context.ip}",
            self._limits.set_password_per_ip,
            self._limits.hourly_window_seconds,
        )
        if retry_after is not None:
            raise RateLimited(retry_after)
        token = await self._password_tokens.get_by_hash(self._generator.hash(secret))
        now = self._clock.now()
        if token is None or not token.is_usable(now):
            raise InvalidToken()
        user = await self._users.get_by_id(token.user_id)
        # A reset link must never reactivate an account an administrator switched off;
        # only an activation link (issued at approval) turns an account on.
        if user is None or (token.purpose is TokenPurpose.RESET and not user.is_active):
            raise InvalidToken()
        validate_password(new_password, user.email)
        user.password_hash = self._hasher.hash(new_password)
        if token.purpose is TokenPurpose.ACTIVATION:
            user.is_active = True
        user.failed_login_count = 0
        user.locked_until = None
        await self._users.save(user)
        token.used_at = now
        await self._password_tokens.save(token)
        # A new password invalidates every existing session.
        await self._refresh_tokens.revoke_all_for_user(user.id, now)
        await self._auditor.record(
            AuditAction.PASSWORD_SET,
            actor=user.id,
            subject=user.email,
            ip=context.ip,
            details={"purpose": token.purpose.value},
        )
        await self._uow.commit()
