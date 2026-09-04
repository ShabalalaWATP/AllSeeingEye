"""Append-only audit trail entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AuditAction(StrEnum):
    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_FAILED = "login_failed"
    ACCOUNT_LOCKED = "account_locked"
    TOKEN_REFRESHED = "token_refreshed"
    REFRESH_REUSE_DETECTED = "refresh_reuse_detected"
    LOGOUT = "logout"
    ACCOUNT_REQUESTED = "account_requested"
    ACCOUNT_REQUEST_APPROVED = "account_request_approved"
    ACCOUNT_REQUEST_REJECTED = "account_request_rejected"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_SET = "password_set"
    USER_UPDATED = "user_updated"
    RESET_LINK_ISSUED = "reset_link_issued"


@dataclass(slots=True)
class AuditEntry:
    at: datetime
    action: AuditAction
    actor_user_id: UUID | None = None
    subject: str | None = None
    ip: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    id: int | None = None
