"""Users and account requests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"


class RequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def normalise_email(email: str) -> str:
    """Emails are compared case-insensitively and stored lower-cased."""
    return email.strip().lower()


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    display_name: str
    role: Role
    is_active: bool
    password_hash: str | None
    failed_login_count: int
    last_failed_at: datetime | None
    locked_until: datetime | None
    created_at: datetime
    last_login_at: datetime | None
    security_version: int = 0

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > now

    def can_log_in(self, now: datetime) -> bool:
        return self.is_active and self.password_hash is not None and not self.is_locked(now)


@dataclass(slots=True)
class AccountRequest:
    id: UUID
    email: str
    display_name: str
    reason: str | None
    status: RequestStatus
    decided_by: UUID | None
    decided_at: datetime | None
    created_at: datetime

    @property
    def is_pending(self) -> bool:
        return self.status is RequestStatus.PENDING
