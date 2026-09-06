"""Personal email-factor enrolment and password-bound security challenges."""

from datetime import timedelta

from ase.application.auth.mfa import MfaUseCase
from ase.application.dto import RequestContext
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, InvalidCredentials, InvalidRequest
from ase.domain.mfa import MfaMethod, MfaPurpose, PendingMfa
from ase.domain.users import Role, User


class MfaManagement:
    def __init__(self, mfa: MfaUseCase) -> None:
        self.mfa = mfa
        self.d = mfa.d

    async def begin(
        self, actor: User, password: str, purpose: MfaPurpose, context: RequestContext
    ) -> PendingMfa:
        user = await self.d.credentials(actor, password, context)
        enabled = await self.d.repo.email_enabled(user.id)
        if purpose is MfaPurpose.EMAIL_ENROL and enabled:
            raise InvalidRequest("Email verification is already enabled.")
        if (
            purpose
            in (MfaPurpose.EMAIL_DISABLE, MfaPurpose.PASSWORD_CHANGE, MfaPurpose.RECOVERY_CODES)
            and not enabled
        ):
            raise InvalidRequest("Email verification is not enabled.")
        if purpose is MfaPurpose.EMAIL_DISABLE:
            await self.require_removable(user)
        pending = await self.mfa.create(user, purpose)
        try:
            return await self.mfa.send_email(pending.challenge_token, context, purpose)
        except InvalidCredentials as exc:
            await self.d.current_actor(actor)
            raise InvalidRequest("The verification request changed. Start a new request.") from exc

    async def confirm(
        self, actor: User, token: str, code: str, purpose: MfaPurpose, context: RequestContext
    ) -> None:
        user = await self.consume_proof(actor, token, code, purpose, context)
        if purpose is MfaPurpose.EMAIL_DISABLE:
            await self.require_removable(user)
        await self.d.repo.set_email_enabled(user.id, purpose is MfaPurpose.EMAIL_ENROL)
        action = (
            AuditAction.MFA_ENABLED
            if purpose is MfaPurpose.EMAIL_ENROL
            else AuditAction.MFA_DISABLED
        )
        await self.d.changed(user, action, context)
        await self.d.uow.commit()

    async def consume_proof(
        self, actor: User, token: str, code: str, purpose: MfaPurpose, context: RequestContext
    ) -> User:
        self.d.limit(context, token)
        await self.d.current_actor(actor)
        # Check ownership before locking any other account. An invalid proof must not
        # trigger the HTTP client's session-refresh flow or consume another user's code.
        candidate = await self.d.repo.get(self.d.generator.hash(token))
        if candidate is None or candidate.user_id != actor.id:
            raise InvalidRequest("The verification code is incorrect, expired or already used.")
        try:
            return await self._consume_proof(actor, token, code, purpose, context)
        except InvalidCredentials as exc:
            raise InvalidRequest(
                "The verification code is incorrect, expired or already used."
            ) from exc

    async def _consume_proof(
        self, actor: User, token: str, code: str, purpose: MfaPurpose, context: RequestContext
    ) -> User:
        challenge, user = await self.d.load(token, purpose)
        if user.id != actor.id or user.security_version != actor.security_version:
            raise InvalidCredentials()
        if not (
            challenge.code_hash
            and challenge.email_sent_at
            and self.d.clock.now() - challenge.email_sent_at < timedelta(minutes=5)
            and self.d.hasher.verify(challenge.code_hash, code)
        ):
            await self.d.fail(challenge, user, context)
        await self.d.consume(challenge)
        return user

    async def require_removable(self, user: User) -> None:
        if user.role is Role.ADMIN and MfaMethod.AUTHENTICATOR not in await self.mfa.methods(user):
            raise InvalidRequest("Administrators must keep at least one MFA method enabled.")

    async def recover_local(self, actor: User, password: str) -> None:
        """Host-only recovery, never exposed as an HTTP operation or login bypass."""
        context = RequestContext(ip=None, user_agent="local-cli")
        user = await self.d.credentials(actor, password, context)
        if user.role is not Role.ADMIN:
            raise Forbidden()
        await self.d.recovery.clear(user.id)
        await self.d.totp.clear(user.id)
        await self.d.repo.set_email_enabled(user.id, False)
        await self.d.changed(user, AuditAction.MFA_RECOVERED, context)
        await self.d.uow.commit()
