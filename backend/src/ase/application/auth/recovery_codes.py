"""Fresh password and existing factor proof protect recovery-code rotation."""

import secrets

from ase.application.auth.current_session import validate_current_session
from ase.application.auth.mfa import MfaUseCase
from ase.application.auth.mfa_management import MfaManagement
from ase.application.dto import AccessClaims, RequestContext
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest
from ase.domain.mfa import MfaMethod, MfaPurpose
from ase.domain.users import User


class RecoveryCodesUseCase:
    def __init__(self, mfa: MfaUseCase) -> None:
        self.mfa = mfa
        self.d = mfa.d

    async def status(self, actor: User) -> tuple[int, bool]:
        user = await self.d.current_actor(actor)
        available = bool(await self.mfa.methods(user))
        return (
            await self.d.recovery.count(user.id, user.security_version) if available else 0,
            available,
        )

    async def generate(
        self,
        actor: User,
        claims: AccessClaims,
        password: str,
        method: MfaMethod,
        code: str,
        token: str | None,
        context: RequestContext,
    ) -> list[str]:
        user = await self.d.credentials(actor, password, context)
        await validate_current_session(claims, self.d.users, self.d.refresh, self.d.clock)
        if method not in await self.mfa.methods(user):
            raise InvalidRequest("Enable and verify an MFA method before creating recovery codes.")
        if method is MfaMethod.EMAIL:
            if not token:
                raise InvalidRequest("Request an email verification code first.")
            user = await MfaManagement(self.mfa).consume_proof(
                actor, token, code, MfaPurpose.RECOVERY_CODES, context
            )
        elif method is MfaMethod.AUTHENTICATOR:
            state = await self.d.totp.get(user.id)
            step = (
                self.d.provider.verify(state.secret_encrypted, code, self.d.clock.now())
                if state and state.secret_encrypted
                else None
            )
            if (
                step is None
                or state is None
                or not state.secret_encrypted
                or not await self.d.totp.consume(user.id, state.secret_encrypted, step)
            ):
                raise InvalidRequest("The authenticator code is incorrect or already used.")
        else:
            raise InvalidRequest("Use your authenticator or email verification method.")
        codes = [secrets.token_hex(16).upper() for _ in range(10)]
        await self.d.recovery.replace(
            user.id, user.security_version, [self.d.generator.hash(code) for code in codes]
        )
        await self.d.auditor.record(
            AuditAction.MFA_RECOVERY_CODES_GENERATED, actor=user.id, ip=context.ip
        )
        await self.d.uow.commit()
        return codes
