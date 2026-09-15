"""Administrator controlled AI allowances and request accounting contracts.

The existing ``llm_usage`` table remains the provider audit trail.  These value objects
describe the separate admission ledger used to stop a request before it reaches a model.
``None`` means unlimited, while zero is an explicit deny-all allowance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from ase.domain.errors import AppError, InvalidRequest

MAX_ALLOWANCE = 2**31 - 1


class AiPolicyScope(StrEnum):
    GLOBAL = "global"
    USER = "user"
    TEAM = "team"


class AiAllowancePeriod(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class AiReservationStatus(StrEnum):
    RESERVED = "reserved"
    SETTLED = "settled"


class AiAllowanceExceeded(AppError):
    """A request cannot be admitted under one of the applicable policies."""

    code = "ai_usage_limit"
    default_message = "The AI usage allowance for this account or team has been reached."

    def __init__(self, policy: AiUsagePolicy | None = None) -> None:
        self.policy_id = policy.id if policy else None
        self.period = policy.period if policy else None
        super().__init__()


def _limit(value: int | None) -> int | None:
    if value is not None and (type(value) is not int or not 0 <= value <= MAX_ALLOWANCE):
        raise InvalidRequest("AI usage limits must be whole numbers from zero upwards.")
    return value


def period_bounds(now: datetime, period: AiAllowancePeriod) -> tuple[datetime, datetime]:
    """Return a UTC calendar window so a period reset is deterministic."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("AI usage periods require timezone-aware datetimes.")
    value = now.astimezone(UTC)
    start = value.replace(hour=0, minute=0, second=0, microsecond=0)
    if period is AiAllowancePeriod.DAY:
        return start, start + timedelta(days=1)
    if period is AiAllowancePeriod.WEEK:
        start -= timedelta(days=start.weekday())
        return start, start + timedelta(days=7)
    if value.month == 12:
        following = start.replace(year=value.year + 1, month=1)
    else:
        following = start.replace(month=value.month + 1)
    return start.replace(day=1), following.replace(day=1)


@dataclass(frozen=True, slots=True)
class AiUsagePolicy:
    id: UUID
    scope: AiPolicyScope
    target_id: UUID | None
    period: AiAllowancePeriod
    request_limit: int | None
    token_limit: int | None
    enabled: bool
    revision: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.scope is AiPolicyScope.GLOBAL and self.target_id is not None:
            raise InvalidRequest("A global AI policy cannot target an account or team.")
        if self.scope is not AiPolicyScope.GLOBAL and self.target_id is None:
            raise InvalidRequest("A user or team AI policy needs a target.")
        if self.revision < 1:
            raise InvalidRequest("AI policy revisions start at one.")
        _limit(self.request_limit)
        _limit(self.token_limit)
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("AI policy timestamps must be timezone-aware.")

    @property
    def unlimited(self) -> bool:
        return self.request_limit is None and self.token_limit is None


@dataclass(frozen=True, slots=True)
class AiUsageSummary:
    policy: AiUsagePolicy
    period_start: datetime
    period_end: datetime
    used_requests: int = 0
    reserved_requests: int = 0
    used_tokens: int = 0
    reserved_tokens: int = 0

    @property
    def remaining_requests(self) -> int | None:
        if self.policy.request_limit is None:
            return None
        return max(0, self.policy.request_limit - self.used_requests - self.reserved_requests)

    @property
    def remaining_tokens(self) -> int | None:
        if self.policy.token_limit is None:
            return None
        return max(0, self.policy.token_limit - self.used_tokens - self.reserved_tokens)


@dataclass(frozen=True, slots=True)
class AiUsageReservation:
    id: UUID
    policy_id: UUID
    user_id: UUID
    profile_id: UUID | None
    model: str
    purpose: str
    period_start: datetime
    period_end: datetime
    reserved_tokens: int
    status: AiReservationStatus
    created_at: datetime
    settled_at: datetime | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    actual_tokens: int | None = None
    ok: bool | None = None
    error: str | None = None


def token_count(value: int | None) -> int | None:
    """Accept only bounded integer provider counts. Unknown values stay unknown."""
    return value if type(value) is int and 0 <= value <= MAX_ALLOWANCE else None
