"""Login: rate limits, lockout, constant-time failure paths, audit."""

from __future__ import annotations

from ase.application.auditing import Auditor
from ase.application.auth.sessions import SessionFactory
from ase.application.dto import AuthSession, RateLimits, RequestContext
from ase.application.ports import Clock, PasswordHasher, RateLimiter, UnitOfWork, UserRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidCredentials, RateLimited
from ase.domain.lockout import LockoutPolicy
from ase.domain.users import User, normalise_email


class LoginUseCase:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        sessions: SessionFactory,
        clock: Clock,
        limiter: RateLimiter,
        limits: RateLimits,
        auditor: Auditor,
        uow: UnitOfWork,
        dummy_hash: str,
        lockout: LockoutPolicy | None = None,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._sessions = sessions
        self._clock = clock
        self._limiter = limiter
        self._limits = limits
        self._auditor = auditor
        self._uow = uow
        self._dummy_hash = dummy_hash
        self._lockout = lockout or LockoutPolicy()

    async def execute(self, email: str, password: str, context: RequestContext) -> AuthSession:
        email = normalise_email(email)
        self._enforce_limits(email, context)
        user = await self._users.get_by_email(email)
        now = self._clock.now()
        if user is None:
            # Burn the same hashing cost as a real check so timing does not reveal existence.
            self._hasher.verify(self._dummy_hash, password)
            await self._fail(None, email, context, "unknown_email")
        elif not user.can_log_in(now):
            self._hasher.verify(self._dummy_hash, password)
            reason = "locked" if user.is_locked(now) else "inactive_or_no_password"
            await self._fail(user, email, context, reason)
        elif not self._hasher.verify(user.password_hash or "", password):
            locked = self._lockout.register_failure(user, now)
            await self._users.save(user)
            if locked:
                await self._auditor.record(
                    AuditAction.ACCOUNT_LOCKED, actor=user.id, subject=email, ip=context.ip
                )
            await self._fail(user, email, context, "wrong_password")
        # Every other branch raised, so this only narrows the type for the checker.
        assert user is not None  # noqa: S101
        self._lockout.register_success(user, now)
        await self._users.save(user)
        session = await self._sessions.start(user, context)
        await self._auditor.record(
            AuditAction.LOGIN_SUCCEEDED, actor=user.id, subject=email, ip=context.ip
        )
        await self._uow.commit()
        return session

    def _enforce_limits(self, email: str, context: RequestContext) -> None:
        window = self._limits.login_window_seconds
        for key, limit in (
            (f"login:ip:{context.ip}", self._limits.login_per_ip),
            (f"login:email:{email}", self._limits.login_per_email),
        ):
            retry_after = self._limiter.hit(key, limit, window)
            if retry_after is not None:
                raise RateLimited(retry_after)

    async def _fail(
        self, user: User | None, email: str, context: RequestContext, reason: str
    ) -> None:
        await self._auditor.record(
            AuditAction.LOGIN_FAILED,
            actor=user.id if user else None,
            subject=email,
            ip=context.ip,
            details={"reason": reason},
        )
        await self._uow.commit()
        raise InvalidCredentials()
