"""Dated, temporary overrides of an AI allowance policy.

Each limit states explicitly how it relates to the base policy: ``inherit`` keeps the
base value, ``limit`` sets a whole-number ceiling, ``unlimited`` removes the ceiling
and ``blocked`` denies every call.  A ``limit`` of zero also denies; zero never means
unlimited.  Among overrides active at the same instant, the most recently created wins.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from ase.domain.errors import InvalidRequest

MAX_OVERRIDE_DURATION = timedelta(days=366)
MAX_OPEN_OVERRIDES = 10
_MAX_LIMIT = 2**31 - 1


class AiLimitState(StrEnum):
    INHERIT = "inherit"
    LIMIT = "limit"
    UNLIMITED = "unlimited"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class AiLimitOverride:
    state: AiLimitState
    value: int | None = None

    def __post_init__(self) -> None:
        if self.state is AiLimitState.LIMIT:
            if type(self.value) is not int or not 0 <= self.value <= _MAX_LIMIT:
                raise InvalidRequest("An override limit must be a whole number from zero upwards.")
        elif self.value is not None:
            raise InvalidRequest("Only an explicit override limit carries a value.")

    def apply(self, base: int | None) -> int | None:
        if self.state is AiLimitState.INHERIT:
            return base
        if self.state is AiLimitState.UNLIMITED:
            return None
        if self.state is AiLimitState.BLOCKED:
            return 0
        return self.value


@dataclass(frozen=True, slots=True)
class AiPolicyOverride:
    id: UUID
    policy_id: UUID
    requests: AiLimitOverride
    tokens: AiLimitOverride
    effective_from: datetime
    expires_at: datetime
    created_by: UUID
    created_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        stamps = (self.effective_from, self.expires_at, self.created_at, self.revoked_at)
        if any(value is not None and value.utcoffset() is None for value in stamps):
            raise ValueError("AI policy override timestamps must be timezone-aware.")
        if self.expires_at <= self.effective_from:
            raise InvalidRequest("An override must expire after it becomes effective.")
        if self.expires_at - self.effective_from > MAX_OVERRIDE_DURATION:
            raise InvalidRequest("A temporary override can last at most 366 days.")

    def active_at(self, now: datetime) -> bool:
        return self.revoked_at is None and self.effective_from <= now < self.expires_at

    def open_at(self, now: datetime) -> bool:
        """Not yet expired and not revoked, including overrides scheduled for later."""
        return self.revoked_at is None and now < self.expires_at


def active_override(
    overrides: Iterable[AiPolicyOverride], now: datetime
) -> AiPolicyOverride | None:
    active = [item for item in overrides if item.active_at(now)]
    if not active:
        return None
    return max(active, key=lambda item: (item.created_at, str(item.id)))
