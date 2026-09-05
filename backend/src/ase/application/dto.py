"""Data transfer objects shared by use cases and the API layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from ase.domain.audit import AuditEntry
from ase.domain.users import Role, User


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    token: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: UUID
    role: Role
    jti: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class RequestContext:
    ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True, slots=True)
class AuthSession:
    access: IssuedAccessToken
    refresh_secret: str
    csrf_token: str
    user: User


@dataclass(frozen=True, slots=True)
class ApprovalResult:
    user: User
    activation_link: str | None
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ResetLinkResult:
    reset_link: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuditPage:
    items: list[AuditEntry] = field(default_factory=list)
    next_before: int | None = None


@dataclass(frozen=True, slots=True)
class RateLimits:
    login_per_ip: int = 10
    login_per_email: int = 5
    login_window_seconds: int = 60
    request_account_per_ip: int = 3
    forgot_per_ip: int = 3
    set_password_per_ip: int = 10
    reports_per_user: int = 10
    hourly_window_seconds: int = 3600
