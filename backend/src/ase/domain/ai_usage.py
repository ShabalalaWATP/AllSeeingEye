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

from ase.domain.ai_usage_overrides import AiPolicyOverride
from ase.domain.errors import AppError, InvalidRequest

MAX_ALLOWANCE = 2**31 - 1
# A reservation this old that never reached a provider is released by reconciliation;
# one that did reach a provider is held as ``unknown`` for administrator review.
STALE_RESERVATION_AGE = timedelta(hours=1)


class AiPolicyScope(StrEnum):
    GLOBAL = "global"
    SYSTEM = "system"
    USER = "user"
    TEAM = "team"


UNTARGETED_SCOPES = frozenset({AiPolicyScope.GLOBAL, AiPolicyScope.SYSTEM})


class AiAllowancePeriod(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class AiReservationStatus(StrEnum):
    RESERVED = "reserved"
    SETTLED = "settled"
    RELEASED = "released"
    UNKNOWN = "unknown"


class AiCallOutcome(StrEnum):
    """How one provider call ended, as far as this process can confirm."""

    COMPLETED = "completed"  # the provider answered; settle reported usage
    FAILED = "failed"  # the provider refused or errored; count the request only
    NOT_DISPATCHED = "not_dispatched"  # nothing was sent; release the reservation
    UNKNOWN = "unknown"  # sent, outcome uncertain; hold the reservation for review


class AiAllowanceExceeded(AppError):
    """A request cannot be admitted under one of the applicable policies."""

    code = "ai_usage_limit"
    default_message = "The AI usage allowance for this account or team has been reached."

    def __init__(self, policy: AiUsagePolicy | None = None) -> None:
        self.policy_id = policy.id if policy else None
        self.period = policy.period if policy else None
        super().__init__()


@dataclass(frozen=True, slots=True)
class AiAttribution:
    """Who a provider call is charged to: an actor (optionally for a team) or the system."""

    user_id: UUID | None
    team_id: UUID | None = None
    system: bool = False

    def __post_init__(self) -> None:
        if self.system and (self.user_id is not None or self.team_id is not None):
            raise ValueError("System AI work cannot also be attributed to an account or team.")
        if not self.system and self.user_id is None:
            raise ValueError("Account AI work needs an initiating account.")

    @classmethod
    def system_work(cls) -> AiAttribution:
        return cls(None, None, True)

    @classmethod
    def actor(cls, user_id: UUID, team_id: UUID | None = None) -> AiAttribution:
        return cls(user_id, team_id, False)


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
        if self.scope in UNTARGETED_SCOPES and self.target_id is not None:
            raise InvalidRequest("A site or system AI policy cannot target an account or team.")
        if self.scope not in UNTARGETED_SCOPES and self.target_id is None:
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
    override: AiPolicyOverride | None = None

    @property
    def request_limit(self) -> int | None:
        if self.override is None:
            return self.policy.request_limit
        return self.override.requests.apply(self.policy.request_limit)

    @property
    def token_limit(self) -> int | None:
        if self.override is None:
            return self.policy.token_limit
        return self.override.tokens.apply(self.policy.token_limit)

    @property
    def remaining_requests(self) -> int | None:
        limit = self.request_limit
        if limit is None:
            return None
        return max(0, limit - self.used_requests - self.reserved_requests)

    @property
    def remaining_tokens(self) -> int | None:
        limit = self.token_limit
        if limit is None:
            return None
        return max(0, limit - self.used_tokens - self.reserved_tokens)


@dataclass(frozen=True, slots=True)
class AiUsageTotals:
    """Observed usage for one attribution bucket, recorded whether or not limits exist."""

    period_start: datetime
    period_end: datetime
    used_requests: int = 0
    used_tokens: int = 0
    unknown_requests: int = 0


@dataclass(frozen=True, slots=True)
class AiMemberUsage:
    user_id: UUID
    display_name: str
    totals: AiUsageTotals


@dataclass(frozen=True, slots=True)
class AiUsageReservation:
    id: UUID
    call_id: UUID
    policy_id: UUID
    user_id: UUID | None
    team_id: UUID | None
    system: bool
    profile_id: UUID | None
    model: str
    purpose: str
    period_start: datetime
    period_end: datetime
    reserved_tokens: int
    status: AiReservationStatus
    created_at: datetime
    dispatched_at: datetime | None = None
    settled_at: datetime | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    actual_tokens: int | None = None
    ok: bool | None = None
    error: str | None = None

    @property
    def attribution(self) -> AiAttribution:
        return AiAttribution(self.user_id, self.team_id, self.system)


def token_count(value: int | None) -> int | None:
    """Accept only bounded integer provider counts. Unknown values stay unknown."""
    return value if type(value) is int and 0 <= value <= MAX_ALLOWANCE else None


def charged_tokens(
    outcome: AiCallOutcome, prompt: int | None, completion: int | None, reserved: int
) -> int:
    """Known counts are charged exactly; a completed call without counts stays conservative."""
    known = token_count(prompt), token_count(completion)
    if outcome is AiCallOutcome.COMPLETED:
        if known[0] is None or known[1] is None:
            return reserved
        return min(MAX_ALLOWANCE, known[0] + known[1])
    if outcome is AiCallOutcome.FAILED:
        return min(MAX_ALLOWANCE, sum(value for value in known if value is not None))
    return 0
