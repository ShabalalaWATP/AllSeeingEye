"""Refresh tokens and single-use password tokens. Only hashes are ever stored."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID


class TokenPurpose(StrEnum):
    ACTIVATION = "activation"
    RESET = "reset"


ACTIVATION_TTL = timedelta(days=7)
RESET_TTL = timedelta(minutes=30)


def ttl_for(purpose: TokenPurpose) -> timedelta:
    return ACTIVATION_TTL if purpose is TokenPurpose.ACTIVATION else RESET_TTL


@dataclass(slots=True)
class RefreshToken:
    id: UUID
    user_id: UUID
    token_hash: str
    family_id: UUID
    parent_id: UUID | None
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    ip: str | None
    user_agent: str | None

    def is_valid(self, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now


@dataclass(slots=True)
class PasswordToken:
    id: UUID
    user_id: UUID
    token_hash: str
    purpose: TokenPurpose
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    def is_usable(self, now: datetime) -> bool:
        return self.used_at is None and self.expires_at > now
