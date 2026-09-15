"""Versioned UTC-month request and output-reservation policy for report work."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ase.domain.errors import InvalidRequest

POLICY_VERSION = "subscription-monthly-budget-v1"
SUBSCRIPTION_CEILING = (240, 8_000_000)
OWNER_CEILING = (800, 24_000_000)


class MonthlyBudgetExhausted(InvalidRequest):
    code = "monthly_budget_exhausted"
    default_message = "This UTC month's report request or output allowance has been reached."


@dataclass(frozen=True, slots=True)
class MonthlyLimit:
    requests: int
    output_tokens: int

    def __post_init__(self) -> None:
        if (
            type(self.requests) is not int
            or type(self.output_tokens) is not int
            or self.requests < 1
            or self.output_tokens < 1
        ):
            raise ValueError("Monthly limits must be positive request and output counts.")


@dataclass(frozen=True, slots=True)
class MonthlyBudgetPolicy:
    owner: MonthlyLimit = MonthlyLimit(*OWNER_CEILING)
    subscription: MonthlyLimit = MonthlyLimit(*SUBSCRIPTION_CEILING)
    version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if (
            self.owner.requests > OWNER_CEILING[0]
            or self.owner.output_tokens > OWNER_CEILING[1]
            or self.subscription.requests > SUBSCRIPTION_CEILING[0]
            or self.subscription.output_tokens > SUBSCRIPTION_CEILING[1]
            or self.version != POLICY_VERSION
        ):
            raise ValueError("Monthly policy may only reduce the versioned ceilings.")


@dataclass(frozen=True, slots=True)
class MonthlyUsage:
    requests: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.requests) is not int
            or type(self.output_tokens) is not int
            or self.requests < 0
            or self.output_tokens < 0
        ):
            raise ValueError("Monthly usage must contain non-negative counts.")

    def add(self, other: MonthlyUsage) -> MonthlyUsage:
        return MonthlyUsage(
            self.requests + other.requests,
            self.output_tokens + other.output_tokens,
        )


def utc_month(at: datetime) -> tuple[datetime, datetime]:
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("Monthly accounting requires an aware dispatch time.")
    value = at.astimezone(UTC)
    start = datetime(value.year, value.month, 1, tzinfo=UTC)
    end = (
        datetime(value.year + 1, 1, 1, tzinfo=UTC)
        if value.month == 12
        else datetime(value.year, value.month + 1, 1, tzinfo=UTC)
    )
    return start, end


def require_monthly_room(
    usage: MonthlyUsage, limit: MonthlyLimit, *, request: int = 1, output_tokens: int = 0
) -> None:
    if (
        type(request) is not int
        or type(output_tokens) is not int
        or request < 0
        or output_tokens < 0
    ):
        raise ValueError("Monthly reservations must be non-negative counts.")
    if (
        usage.requests + request > limit.requests
        or usage.output_tokens + output_tokens > limit.output_tokens
    ):
        raise MonthlyBudgetExhausted()
