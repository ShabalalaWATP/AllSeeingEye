"""Shared MFA dependencies and atomic challenge authorisation."""

from dataclasses import dataclass

from ase.application.auditing import Auditor
from ase.application.auth.sessions import SessionFactory
from ase.application.dto import RequestContext
from ase.application.ports import (
    Clock,
    EmailSender,
    PasswordHasher,
    RateLimiter,
    RefreshTokenRepository,
    TokenGenerator,
    UnitOfWork,
    UserRepository,
)
from ase.application.ports.mfa import MfaRepository
from ase.application.ports.totp import TotpProvider, TotpRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidCredentials, InvalidRequest, RateLimited, Unauthenticated
from ase.domain.lockout import LockoutPolicy
from ase.domain.mfa import MfaChallenge, MfaPurpose
from ase.domain.users import User


@dataclass(frozen=True)
class MfaContext:
    repo: MfaRepository
    totp: TotpRepository
    provider: TotpProvider
    users: UserRepository
    hasher: PasswordHasher
    generator: TokenGenerator
    email: EmailSender
    clock: Clock
    limiter: RateLimiter
    auditor: Auditor
    uow: UnitOfWork
    refresh: RefreshTokenRepository
    sessions: SessionFactory

    def limit(self, context: RequestContext, token: str, *, sending: bool = False) -> None:
        prefix = "mfa-send" if sending else "mfa"
        for key, count in (
            (f"{prefix}:ip:{context.ip}", 20),
            (f"{prefix}:token:{self.generator.hash(token)}", 5),
        ):
            retry = self.limiter.hit(key, count, 300)
            if retry is not None:
                raise RateLimited(retry)

    async def load(self, token: str, purpose: MfaPurpose) -> tuple[MfaChallenge, User]:
        challenge = await self.repo.get(self.generator.hash(token))
        if challenge is None:
            raise InvalidCredentials()
        # User lock serialises factor changes and challenge completion across workers.
        user = await self.users.lock_by_id(challenge.user_id)
        challenge = await self.repo.get(self.generator.hash(token))
        now = self.clock.now()
        if (
            challenge is None
            or user is None
            or not user.can_log_in(now)
            or challenge.security_version != user.security_version
            or challenge.purpose is not purpose
            or challenge.expires_at <= now
            or challenge.consumed_at is not None
            or challenge.attempts >= 5
        ):
            raise InvalidCredentials()
        return challenge, user

    async def save(self, challenge: MfaChallenge) -> None:
        revision = challenge.revision
        if not await self.repo.save(challenge, revision):
            raise InvalidCredentials()
        challenge.revision = revision + 1

    async def consume(self, challenge: MfaChallenge) -> None:
        challenge.consumed_at = self.clock.now()
        challenge.code_hash = None
        challenge.pending_encrypted = None
        await self.save(challenge)

    async def fail(self, challenge: MfaChallenge, user: User, context: RequestContext) -> None:
        challenge.attempts += 1
        await self.save(challenge)
        if LockoutPolicy().register_failure(user, self.clock.now()):
            await self.auditor.record(AuditAction.ACCOUNT_LOCKED, actor=user.id, ip=context.ip)
        await self.users.save(user)
        await self.auditor.record(
            AuditAction.LOGIN_FAILED,
            actor=user.id,
            ip=context.ip,
            details={"reason": "invalid_second_factor"},
        )
        await self.uow.commit()
        raise InvalidCredentials()

    async def credentials(self, actor: User, password: str, context: RequestContext) -> User:
        self.limit(context, str(actor.id))
        current = await self.current_actor(actor)
        if not current.can_log_in(self.clock.now()) or not self.hasher.verify(
            current.password_hash or "", password
        ):
            raise InvalidRequest("The current password is incorrect or the account is locked.")
        return current

    async def current_actor(self, actor: User) -> User:
        """Distinguish an ended session from an incorrect personal security proof."""
        current = await self.users.lock_by_id(actor.id)
        if (
            current is None
            or current.security_version != actor.security_version
            or not current.is_active
        ):
            raise Unauthenticated("The session has ended. Sign in again.")
        return current

    async def changed(self, user: User, action: AuditAction, context: RequestContext) -> None:
        user.security_version += 1
        await self.users.save(user)
        await self.refresh.revoke_all_for_user(user.id, self.clock.now())
        await self.auditor.record(action, actor=user.id, ip=context.ip)
