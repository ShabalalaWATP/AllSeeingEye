"""Optional administrator TOTP enrolment, verification and removal."""

from datetime import timedelta

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.policy import require_admin
from ase.application.ports import (
    Clock,
    PasswordHasher,
    RateLimiter,
    RefreshTokenRepository,
    UnitOfWork,
)
from ase.application.ports.totp import TotpProvider, TotpRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, InvalidRequest, RateLimited
from ase.domain.totp import TotpEnrolment
from ase.domain.users import User


class TotpUseCase:
    def __init__(
        self,
        repository: TotpRepository,
        provider: TotpProvider,
        hasher: PasswordHasher,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
        limiter: RateLimiter,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._repo = repository
        self._provider = provider
        self._hasher = hasher
        self._refresh = refresh_tokens
        self._clock = clock
        self._limiter = limiter
        self._auditor = auditor
        self._uow = uow

    async def status(self, actor: User) -> tuple[bool, bool]:
        self._require_active_admin(actor)
        state = await self._repo.get(actor.id)
        return bool(state and state.enabled), self._provider.available

    async def begin(self, actor: User, password: str, context: RequestContext) -> TotpEnrolment:
        await self._authorise(actor, password, context)
        enrolment = self._provider.enrol(actor.email)
        if not await self._repo.begin(
            actor.id,
            enrolment.encrypted,
            self._clock.now() + timedelta(minutes=10),
        ):
            raise InvalidRequest("TOTP is already enabled or enrolment changed. Refresh and retry.")
        await self._record(AuditAction.TOTP_ENROLMENT_STARTED, actor, context)
        return enrolment

    async def confirm(self, actor: User, code: str, context: RequestContext) -> None:
        self._require_active_admin(actor)
        self._limit(actor, context)
        state = await self._repo.get(actor.id)
        now = self._clock.now()
        if (
            state is None
            or state.enabled
            or state.pending_encrypted is None
            or state.pending_expires_at is None
            or state.pending_expires_at <= now
        ):
            raise InvalidRequest("Start a new TOTP enrolment before confirming a code.")
        step = self._provider.verify(state.pending_encrypted, code, now)
        if step is None or not await self._repo.confirm(
            actor.id, state.pending_encrypted, step, now
        ):
            await self._failure(actor, context)
        await self._refresh.revoke_all_for_user(actor.id, now)
        await self._record(AuditAction.TOTP_ENABLED, actor, context)

    async def verify_login(self, user: User, code: str | None) -> bool:
        """The caller applies login rate limits and commits code consumption with the session."""
        if not user.is_admin:
            return True
        state = await self._repo.get(user.id)
        if state is None or state.secret_encrypted is None:
            return True
        step = self._provider.verify(state.secret_encrypted, code or "", self._clock.now())
        return step is not None and await self._repo.consume(user.id, state.secret_encrypted, step)

    async def disable(
        self,
        actor: User,
        password: str,
        code: str,
        context: RequestContext,
    ) -> None:
        await self._authorise(actor, password, context)
        state = await self._repo.get(actor.id)
        if state is None or not state.enabled:
            raise InvalidRequest("TOTP is not enabled.")
        if not await self.verify_login(actor, code):
            await self._failure(actor, context)
        await self._remove(actor, context, AuditAction.TOTP_DISABLED)

    async def recover_local(self, actor: User, password: str) -> None:
        """Host-only recovery, deliberately unavailable through any HTTP route."""
        context = RequestContext(ip=None, user_agent="local-cli")
        await self._authorise(actor, password, context)
        await self._remove(actor, context, AuditAction.TOTP_RECOVERED)

    async def _remove(self, actor: User, context: RequestContext, action: AuditAction) -> None:
        await self._repo.clear(actor.id)
        await self._refresh.revoke_all_for_user(actor.id, self._clock.now())
        await self._record(action, actor, context)

    async def _authorise(self, actor: User, password: str, context: RequestContext) -> None:
        self._require_active_admin(actor)
        self._limit(actor, context)
        if not actor.can_log_in(self._clock.now()) or not self._hasher.verify(
            actor.password_hash or "",
            password,
        ):
            await self._failure(actor, context)

    def _limit(self, actor: User, context: RequestContext) -> None:
        for key in (f"totp:user:{actor.id}", f"totp:ip:{context.ip}"):
            retry = self._limiter.hit(key, 5, 60)
            if retry is not None:
                raise RateLimited(retry)

    @staticmethod
    def _require_active_admin(actor: User) -> None:
        require_admin(actor)
        if not actor.is_active:
            raise Forbidden()

    async def _failure(self, actor: User, context: RequestContext) -> None:
        await self._record(AuditAction.TOTP_FAILED, actor, context)
        raise InvalidRequest(
            "The password or authenticator code is incorrect, expired or already used."
        )

    async def _record(self, action: AuditAction, actor: User, context: RequestContext) -> None:
        await self._auditor.record(action, actor=actor.id, ip=context.ip)
        await self._uow.commit()
