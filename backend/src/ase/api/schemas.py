"""Request and response models. Inputs are validated at the boundary; outputs never leak hashes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from ase.application.dto import AuthSession
from ase.domain.audit import AuditEntry
from ase.domain.session_activity import SessionActivity
from ase.domain.users import AccountRequest, RequestStatus, Role, User


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RequestAccountIn(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    reason: str | None = Field(default=None, max_length=1000)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class SetPasswordIn(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=1, max_length=128)


# Keep legacy manager readable in outputs while accurately describing assignable
# roles in validation and OpenAPI. Team leadership is a separate membership.
AssignableRole = Literal[Role.USER, Role.ADMIN]


class ApproveIn(BaseModel):
    role: AssignableRole = Role.USER


class RejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class UpdateUserIn(BaseModel):
    role: AssignableRole | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_user(cls, user: User) -> Self:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class SessionActivityOut(BaseModel):
    server_now: datetime
    last_activity_at: datetime
    idle_expires_at: datetime
    idle_minutes: int

    @classmethod
    def from_activity(cls, activity: SessionActivity) -> Self:
        return cls(
            server_now=activity.server_now,
            last_activity_at=activity.last_activity_at,
            idle_expires_at=activity.idle_expires_at,
            idle_minutes=activity.idle_minutes,
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
    user: UserOut
    activity: SessionActivityOut

    @classmethod
    def from_session(cls, session: AuthSession) -> Self:
        return cls(
            access_token=session.access.token,
            expires_in=session.access.expires_in,
            user=UserOut.from_user(session.user),
            activity=SessionActivityOut.from_activity(session.activity),
        )


class MessageOut(BaseModel):
    message: str


class ForgotPasswordOut(MessageOut):
    email_available: bool


class AccountRequestOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    reason: str | None
    status: RequestStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, request: AccountRequest) -> Self:
        return cls(
            id=request.id,
            email=request.email,
            display_name=request.display_name,
            reason=request.reason,
            status=request.status,
            created_at=request.created_at,
        )


class AccountRequestsOut(BaseModel):
    items: list[AccountRequestOut]


class ApproveOut(BaseModel):
    user: UserOut
    activation_link: str | None
    expires_at: datetime


class UsersOut(BaseModel):
    items: list[UserOut]


class ResetLinkOut(BaseModel):
    reset_link: str
    expires_at: datetime


class AuditEntryOut(BaseModel):
    id: int
    at: datetime
    actor_user_id: UUID | None
    action: str
    subject: str | None
    ip: str | None
    details: dict[str, object]

    @classmethod
    def from_entity(cls, entry: AuditEntry) -> Self:
        return cls(
            id=entry.id or 0,
            at=entry.at,
            actor_user_id=entry.actor_user_id,
            action=entry.action.value,
            subject=entry.subject,
            ip=entry.ip,
            details=dict(entry.details),
        )


class AuditPageOut(BaseModel):
    items: list[AuditEntryOut]
    next_before: int | None


class HealthOut(BaseModel):
    status: str


class PublicSiteOut(BaseModel):
    """Facts the signed-out pages need about this installation; nothing private."""

    product_page_enabled: bool
    enterprise_enquiries_enabled: bool
    enterprise_enquiry_retention_days: int


class ReadyOut(BaseModel):
    status: str
