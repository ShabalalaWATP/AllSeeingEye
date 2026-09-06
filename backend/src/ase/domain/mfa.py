"""Restricted, single-use second-factor challenges. Never access sessions."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MfaMethod(StrEnum):
    AUTHENTICATOR = "authenticator"
    EMAIL = "email"


class MfaPurpose(StrEnum):
    LOGIN = "login"
    EMAIL_ENROL = "email_enrol"
    EMAIL_DISABLE = "email_disable"
    PASSWORD_CHANGE = "password_change"  # noqa: S105


@dataclass(slots=True)
class MfaChallenge:
    token_hash: str
    user_id: UUID
    security_version: int
    purpose: MfaPurpose
    expires_at: datetime
    enrollment_required: bool = False
    attempts: int = 0
    revision: int = 0
    code_hash: str | None = field(default=None, repr=False)
    email_sent_at: datetime | None = None
    pending_encrypted: str | None = field(default=None, repr=False)
    consumed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PendingMfa:
    challenge_token: str = field(repr=False)
    expires_at: datetime
    methods: tuple[MfaMethod, ...]
    enrollment_required: bool
    email_sent: bool
