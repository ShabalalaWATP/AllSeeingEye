"""Account request review: list, approve (with activation link) and reject."""

from __future__ import annotations

from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import ApprovalResult, RequestContext
from ase.application.policy import require_admin
from ase.application.ports import (
    AccountRequestRepository,
    Clock,
    EmailSender,
    LinkBuilder,
    PasswordTokenRepository,
    TokenGenerator,
    UnitOfWork,
    UserRepository,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import AlreadyDecided, EmailTaken, NotFound
from ase.domain.tokens import PasswordToken, TokenPurpose, ttl_for
from ase.domain.users import AccountRequest, RequestStatus, Role, User


class ListRequestsUseCase:
    def __init__(self, requests: AccountRequestRepository) -> None:
        self._requests = requests

    async def execute(self, actor: User, status: RequestStatus) -> list[AccountRequest]:
        require_admin(actor)
        return await self._requests.list_by_status(status)


class ApproveRequestUseCase:
    def __init__(
        self,
        users: UserRepository,
        requests: AccountRequestRepository,
        password_tokens: PasswordTokenRepository,
        generator: TokenGenerator,
        links: LinkBuilder,
        email_sender: EmailSender,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._requests = requests
        self._password_tokens = password_tokens
        self._generator = generator
        self._links = links
        self._email_sender = email_sender
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self, actor: User, request_id: UUID, role: Role, context: RequestContext
    ) -> ApprovalResult:
        require_admin(actor)
        request = await self._requests.get(request_id)
        if request is None:
            raise NotFound()
        if not request.is_pending:
            raise AlreadyDecided()
        if await self._users.get_by_email(request.email) is not None:
            raise EmailTaken()
        now = self._clock.now()
        user = User(
            id=uuid4(),
            email=request.email,
            display_name=request.display_name,
            role=role,
            is_active=True,
            password_hash=None,
            failed_login_count=0,
            last_failed_at=None,
            locked_until=None,
            created_at=now,
            last_login_at=None,
        )
        await self._users.add(user)
        request.status = RequestStatus.APPROVED
        request.decided_by = actor.id
        request.decided_at = now
        await self._requests.save(request)
        secret = self._generator.new_secret()
        expires_at = now + ttl_for(TokenPurpose.ACTIVATION)
        await self._password_tokens.add(
            PasswordToken(
                id=uuid4(),
                user_id=user.id,
                token_hash=self._generator.hash(secret),
                purpose=TokenPurpose.ACTIVATION,
                expires_at=expires_at,
                used_at=None,
                created_at=now,
            )
        )
        link = self._links.link_for(TokenPurpose.ACTIVATION, secret)
        delivered = await self._email_sender.send_link(user.email, TokenPurpose.ACTIVATION, link)
        await self._auditor.record(
            AuditAction.ACCOUNT_REQUEST_APPROVED,
            actor=actor.id,
            subject=user.email,
            ip=context.ip,
            details={"role": role.value, "delivered": delivered},
        )
        await self._uow.commit()
        return ApprovalResult(
            user=user, activation_link=None if delivered else link, expires_at=expires_at
        )


class RejectRequestUseCase:
    def __init__(
        self,
        requests: AccountRequestRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._requests = requests
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self, actor: User, request_id: UUID, reason: str | None, context: RequestContext
    ) -> None:
        require_admin(actor)
        request = await self._requests.get(request_id)
        if request is None:
            raise NotFound()
        if not request.is_pending:
            raise AlreadyDecided()
        request.status = RequestStatus.REJECTED
        request.decided_by = actor.id
        request.decided_at = self._clock.now()
        await self._requests.save(request)
        await self._auditor.record(
            AuditAction.ACCOUNT_REQUEST_REJECTED,
            actor=actor.id,
            subject=request.email,
            ip=context.ip,
            details={"reason": reason or ""},
        )
        await self._uow.commit()
