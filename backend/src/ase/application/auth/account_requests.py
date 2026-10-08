"""Public account and password reset requests. Neither reveals whether an email exists."""

from __future__ import annotations

from uuid import uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RateLimits, RequestContext
from ase.application.ports import (
    AccountRequestRepository,
    Clock,
    EmailSender,
    LinkBuilder,
    PasswordTokenRepository,
    RateLimiter,
    TokenGenerator,
    UnitOfWork,
    UserRepository,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import RateLimited
from ase.domain.tokens import PasswordToken, TokenPurpose, ttl_for
from ase.domain.users import AccountRequest, RequestStatus, normalise_email


def _enforce(limiter: RateLimiter, window: int, *buckets: tuple[str, int]) -> None:
    # Per-client buckets come first so one client cannot spend the shared allowance
    # beyond its own limit.
    for key, limit in buckets:
        retry_after = limiter.hit(key, limit, window)
        if retry_after is not None:
            raise RateLimited(retry_after)


class RequestAccountUseCase:
    def __init__(
        self,
        users: UserRepository,
        requests: AccountRequestRepository,
        clock: Clock,
        limiter: RateLimiter,
        limits: RateLimits,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._requests = requests
        self._clock = clock
        self._limiter = limiter
        self._limits = limits
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self, email: str, display_name: str, reason: str | None, context: RequestContext
    ) -> None:
        _enforce(
            self._limiter,
            self._limits.hourly_window_seconds,
            (f"request-account:ip:{context.client_key}", self._limits.request_account_per_ip),
            ("request-account:global", self._limits.request_account_global),
        )
        email = normalise_email(email)
        duplicate = await self._users.get_by_email(
            email
        ) is not None or await self._requests.has_pending_for_email(email)
        # A full review queue drops new requests behind the same response, so callers
        # learn nothing about the queue or the address. Administrators see it in audit.
        queue_full = (
            not duplicate
            and await self._requests.count_pending() >= self._limits.pending_account_requests_max
        )
        if not duplicate and not queue_full:
            await self._requests.add(
                AccountRequest(
                    id=uuid4(),
                    email=email,
                    display_name=display_name.strip(),
                    reason=reason.strip() if reason else None,
                    status=RequestStatus.PENDING,
                    decided_by=None,
                    decided_at=None,
                    created_at=self._clock.now(),
                )
            )
        await self._auditor.record(
            AuditAction.ACCOUNT_REQUESTED,
            subject=email,
            ip=context.ip,
            details={"duplicate": duplicate, "queue_full": queue_full},
        )
        await self._uow.commit()


class ForgotPasswordUseCase:
    def __init__(
        self,
        users: UserRepository,
        password_tokens: PasswordTokenRepository,
        generator: TokenGenerator,
        links: LinkBuilder,
        email_sender: EmailSender,
        clock: Clock,
        limiter: RateLimiter,
        limits: RateLimits,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._password_tokens = password_tokens
        self._generator = generator
        self._links = links
        self._email_sender = email_sender
        self._clock = clock
        self._limiter = limiter
        self._limits = limits
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self, email: str, context: RequestContext, *, send_email: bool = True
    ) -> str | None:
        _enforce(
            self._limiter,
            self._limits.hourly_window_seconds,
            (f"forgot:ip:{context.client_key}", self._limits.forgot_per_ip),
            ("forgot:global", self._limits.forgot_global),
        )
        email = normalise_email(email)
        user = await self._users.lock_by_email(email)
        link: str | None = None
        if user is not None and user.is_active and user.password_hash is not None:
            now = self._clock.now()
            secret = self._generator.new_secret()
            await self._password_tokens.add(
                PasswordToken(
                    id=uuid4(),
                    user_id=user.id,
                    token_hash=self._generator.hash(secret),
                    purpose=TokenPurpose.RESET,
                    expires_at=now + ttl_for(TokenPurpose.RESET),
                    used_at=None,
                    created_at=now,
                )
            )
            link = self._links.link_for(TokenPurpose.RESET, secret)
        await self._auditor.record(
            AuditAction.PASSWORD_RESET_REQUESTED,
            actor=user.id if user else None,
            subject=email,
            ip=context.ip,
            details={"delivery_requested": link is not None},
        )
        await self._uow.commit()
        # The account lock and token transaction must end before external SMTP I/O.
        if link is not None and send_email:
            await self._email_sender.send_link(email, TokenPurpose.RESET, link)
        return link
