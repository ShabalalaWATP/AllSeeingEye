"""Password-bound MFA login, delivery and restricted administrator enrolment."""

import secrets
from datetime import timedelta

from ase.application.auth.mfa_context import MfaContext
from ase.application.dto import AuthSession, RequestContext
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidCredentials, InvalidRequest
from ase.domain.lockout import LockoutPolicy
from ase.domain.mfa import MfaChallenge, MfaMethod, MfaPurpose, PendingMfa
from ase.domain.totp import TotpEnrolment
from ase.domain.users import Role, User


class MfaUseCase:
    def __init__(self, dependencies: MfaContext) -> None:
        self.d = dependencies

    async def methods(self, user: User) -> tuple[MfaMethod, ...]:
        state = await self.d.totp.get(user.id)
        result = []
        if state and state.enabled:
            result.append(MfaMethod.AUTHENTICATOR)
        if await self.d.repo.email_enabled(user.id):
            result.append(MfaMethod.EMAIL)
        return tuple(result)

    def available_methods(self) -> tuple[MfaMethod, ...]:
        return tuple(
            method
            for method, available in (
                (MfaMethod.AUTHENTICATOR, self.d.provider.available),
                (MfaMethod.EMAIL, self.d.email.available),
            )
            if available
        )

    async def begin(self, user: User, context: RequestContext) -> PendingMfa | None:
        methods = await self.methods(user)
        required = user.role is Role.ADMIN and not methods
        if not methods and not required:
            return None
        if required and not self.available_methods():
            raise InvalidRequest(
                "MFA must be configured before administrator sign-in. "
                "Ask the host operator to configure encryption or email delivery."
            )
        pending = await self.create(user, MfaPurpose.LOGIN, required)
        if methods == (MfaMethod.EMAIL,):
            return await self.send_email(pending.challenge_token, context)
        return pending

    async def create(
        self, user: User, purpose: MfaPurpose, enrollment_required: bool = False
    ) -> PendingMfa:
        secret = self.d.generator.new_secret()
        challenge = MfaChallenge(
            self.d.generator.hash(secret),
            user.id,
            user.security_version,
            purpose,
            self.d.clock.now() + timedelta(minutes=10),
            enrollment_required=enrollment_required,
        )
        await self.d.repo.add(challenge)
        await self.d.uow.commit()
        return await self.pending(secret, challenge, user)

    async def pending(self, secret: str, challenge: MfaChallenge, user: User) -> PendingMfa:
        methods = (
            self.available_methods() if challenge.enrollment_required else await self.methods(user)
        )
        if challenge.purpose is not MfaPurpose.LOGIN:
            methods = (MfaMethod.EMAIL,)
        return PendingMfa(
            secret,
            challenge.expires_at,
            methods,
            challenge.enrollment_required,
            challenge.email_sent_at is not None,
        )

    async def send_email(
        self, token: str, context: RequestContext, purpose: MfaPurpose = MfaPurpose.LOGIN
    ) -> PendingMfa:
        self.d.limit(context, token, sending=True)
        challenge, user = await self.d.load(token, purpose)
        if not self.d.email.available:
            raise InvalidRequest("Email verification is unavailable. Contact your administrator.")
        if (
            purpose is MfaPurpose.LOGIN
            and not challenge.enrollment_required
            and MfaMethod.EMAIL not in await self.methods(user)
        ):
            raise InvalidCredentials()
        now = self.d.clock.now()
        if challenge.email_sent_at and now - challenge.email_sent_at < timedelta(seconds=60):
            raise InvalidRequest("Wait a minute before requesting another code.")
        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge.code_hash = self.d.hasher.hash(code)
        challenge.email_sent_at = None
        await self.d.save(challenge)
        revision = challenge.revision
        await self.d.uow.commit()
        delivered = await self.d.email.send_code(user.email, code)
        # Delivery never holds a database lock. Reject stale or superseded delivery results.
        current, user = await self.d.load(token, purpose)
        if current.revision != revision:
            raise InvalidCredentials()
        current.email_sent_at = self.d.clock.now() if delivered else None
        if not delivered:
            current.code_hash = None
        await self.d.save(current)
        await self.d.uow.commit()
        if not delivered:
            raise InvalidRequest("The verification email could not be sent. Try again later.")
        return await self.pending(token, current, user)

    async def enrol_app(self, token: str, context: RequestContext) -> TotpEnrolment:
        self.d.limit(context, token)
        challenge, user = await self.d.load(token, MfaPurpose.LOGIN)
        if not challenge.enrollment_required or await self.methods(user):
            raise InvalidCredentials()
        enrolment = self.d.provider.enrol(user.email)
        if not await self.d.totp.begin(user.id, enrolment.encrypted, challenge.expires_at):
            raise InvalidRequest("Authenticator enrolment changed. Sign in again.")
        challenge.pending_encrypted = enrolment.encrypted
        await self.d.save(challenge)
        await self.d.uow.commit()
        return enrolment

    async def verify(
        self, token: str, method: MfaMethod, code: str, context: RequestContext
    ) -> AuthSession:
        self.d.limit(context, token)
        challenge, user = await self.d.load(token, MfaPurpose.LOGIN)
        if not await self.verify_factor(challenge, user, method, code):
            await self.d.fail(challenge, user, context)
        if challenge.enrollment_required:
            if method is MfaMethod.EMAIL:
                await self.d.repo.set_email_enabled(user.id, True)
            await self.d.changed(user, AuditAction.MFA_ENABLED, context)
        await self.d.consume(challenge)
        LockoutPolicy().register_success(user, self.d.clock.now())
        await self.d.users.save(user)
        session = await self.d.sessions.start(user, context, mfa_verified=True)
        await self.d.auditor.record(AuditAction.LOGIN_SUCCEEDED, actor=user.id, ip=context.ip)
        await self.d.uow.commit()
        return session

    async def verify_factor(
        self, challenge: MfaChallenge, user: User, method: MfaMethod, code: str
    ) -> bool:
        methods = await self.methods(user)
        if (challenge.enrollment_required and methods) or (
            not challenge.enrollment_required and method not in methods
        ):
            return False
        if method is MfaMethod.EMAIL:
            return bool(
                challenge.email_sent_at
                and challenge.code_hash
                and self.d.clock.now() - challenge.email_sent_at < timedelta(minutes=5)
                and self.d.hasher.verify(challenge.code_hash, code)
            )
        state = await self.d.totp.get(user.id)
        if challenge.enrollment_required:
            encrypted = challenge.pending_encrypted
            if not encrypted or not state or state.pending_encrypted != encrypted:
                return False
            step = self.d.provider.verify(encrypted, code, self.d.clock.now())
            return step is not None and await self.d.totp.confirm(
                user.id, encrypted, step, self.d.clock.now()
            )
        if not state or not state.secret_encrypted:
            return False
        step = self.d.provider.verify(state.secret_encrypted, code, self.d.clock.now())
        return step is not None and await self.d.totp.consume(user.id, state.secret_encrypted, step)
