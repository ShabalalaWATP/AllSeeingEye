"""Research allowances count admitted runs, independently of model-call budgets."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from ase.domain.errors import InvalidRequest, RateLimited

ResearchTier = Literal[1, 2, 3, 4, 5]
ResearchPeriod = Literal["day", "week"]


@dataclass(frozen=True, slots=True)
class ResearchTierPolicy:
    tier: ResearchTier
    label: str
    limit: int | None
    period: ResearchPeriod


TIERS = (
    ResearchTierPolicy(1, "Level 1", 4, "week"),
    ResearchTierPolicy(2, "Level 2", 4, "day"),
    ResearchTierPolicy(3, "Level 3", 13, "day"),
    ResearchTierPolicy(4, "Level 4", 32, "day"),
    ResearchTierPolicy(5, "Level 5", None, "day"),
)


def tier_policy(tier: int) -> ResearchTierPolicy:
    if type(tier) is not int or tier not in (1, 2, 3, 4, 5):
        raise InvalidRequest("Choose a research level from 1 to 5.")
    return TIERS[tier - 1]


def period_bounds(now: datetime, period: ResearchPeriod) -> tuple[datetime, datetime]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Research usage periods require timezone-aware datetimes.")
    start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start -= timedelta(days=start.weekday())
    return start, start + timedelta(days=7 if period == "week" else 1)


@dataclass(frozen=True, slots=True)
class ResearchAllowance:
    tier: ResearchTier
    label: str
    limit: int | None
    period: ResearchPeriod
    used: int
    remaining: int | None
    period_start: datetime
    resets_at: datetime
    revision: int


class ResearchUsageLimit(RateLimited):
    code = "research_usage_limit"

    def __init__(self, allowance: ResearchAllowance, now: datetime) -> None:
        self.resets_at = allowance.resets_at
        super().__init__(int((allowance.resets_at - now).total_seconds()) + 1)
        self.message = (
            f"Your {allowance.label} allowance of {allowance.limit} research runs per "
            f"{allowance.period} is used up. It resets at "
            f"{allowance.resets_at:%Y-%m-%d %H:%M} UTC. Subscriptions share this allowance."
        )
        self.args = (self.message,)
