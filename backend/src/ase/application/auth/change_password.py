"""Change the signed-in account's password and atomically end every previous session."""

from ase.application.auditing import Auditor
from ase.application.auth.mfa_management import MfaManagement
from ase.application.auth.totp import TotpUseCase
from ase.application.dto import RequestContext
from ase.application.ports import (
    Clock,
    PasswordHasher,
    PasswordTokenRepository,
    RateLimiter,
    RefreshTokenRepository,
    UnitOfWork,
    UserRepository,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest, RateLimited, Unauthenticated
from ase.domain.mfa import MfaMethod, MfaPurpose
from ase.domain.password_policy import validate_password
from ase.domain.users import User


class ChangePasswordUseCase:
    def __init__(
        self,
        users: UserRepository,
        password_tokens: PasswordTokenRepository,
        refresh_tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        totp: TotpUseCase,
        clock: Clock,
        limiter: RateLimiter,
        auditor: Auditor,
        uow: UnitOfWork,
        mfa: MfaManagement,
    ) -> None:
        self._users = users
        self._password_tokens = password_tokens
        self._refresh_tokens = refresh_tokens
        self._hasher = hasher
        self._totp = totp
        self._clock = clock
        self._limiter = limiter
        self._auditor = auditor
        self._uow = uow
        self._mfa = mfa

    async def execute(
        self,
        actor: User,
        current_password: str,
        new_password: str,
        context: RequestContext,
        totp_code: str | None = None,
        mfa_challenge_token: str | None = None,
        mfa_code: str | None = None,
    ) -> None:
        for key in (f"change-password:user:{actor.id}", f"change-password:ip:{context.ip}"):
            retry = self._limiter.hit(key, 5, 60)
            if retry is not None:
                raise RateLimited(retry)
        current = await self._users.lock_by_id(actor.id)
        if (
            current is None
            or not current.is_active
            or current.security_version != actor.security_version
        ):
            raise Unauthenticated("The session has ended. Sign in again.")
        now = self._clock.now()
        if not current.can_log_in(now) or not self._hasher.verify(
            current.password_hash or "", current_password
        ):
            await self._failed(current, context)
        validate_password(new_password, current.email)
        # Stored factors remain effective for every account role, including a demoted admin.
        # Consumption commits with the credential change, so failed transactions cannot burn a code.
        methods = await self._mfa.mfa.methods(current)
        if mfa_challenge_token and mfa_code and MfaMethod.EMAIL in methods:
            await self._mfa.consume_proof(
                current, mfa_challenge_token, mfa_code, MfaPurpose.PASSWORD_CHANGE, context
            )
        elif MfaMethod.AUTHENTICATOR in methods:
            if not await self._totp.verify_login(current, totp_code):
                await self._failed(current, context)
        elif methods:
            await self._failed(current, context)
        current.password_hash = self._hasher.hash(new_password)
        current.security_version += 1
        current.failed_login_count = 0
        current.last_failed_at = None
        current.locked_until = None
        await self._users.save(current)
        await self._refresh_tokens.revoke_all_for_user(current.id, now)
        await self._password_tokens.revoke_all_for_user(current.id, now)
        await self._auditor.record(AuditAction.PASSWORD_CHANGED, actor=current.id, ip=context.ip)
        await self._uow.commit()

    async def _failed(self, actor: User, context: RequestContext) -> None:
        await self._auditor.record(
            AuditAction.PASSWORD_CHANGE_FAILED, actor=actor.id, ip=context.ip
        )
        await self._uow.commit()
        raise InvalidRequest(
            "The current password or authenticator code is incorrect, expired or already used."
        )
