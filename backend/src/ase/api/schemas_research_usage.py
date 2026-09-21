"""Research-run allowances, separately from individual provider calls and tokens."""

from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.research_usage import ResearchAllowance


class ResearchAllowanceOut(BaseModel):
    tier: Literal[1, 2, 3, 4, 5]
    label: str
    limit: int | None
    period: Literal["day", "week"]
    used: int
    remaining: int | None
    period_start: datetime
    resets_at: datetime
    revision: int

    @classmethod
    def from_allowance(cls, allowance: ResearchAllowance) -> "ResearchAllowanceOut":
        return cls(**asdict(allowance))


class UserResearchAllowanceOut(ResearchAllowanceOut):
    user_id: UUID


class ResearchTierOut(BaseModel):
    tier: Literal[1, 2, 3, 4, 5]
    label: str
    limit: int | None
    period: Literal["day", "week"]


class ResearchUsagePageOut(BaseModel):
    tiers: list[ResearchTierOut]
    items: list[UserResearchAllowanceOut]


class ResearchTierIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tier: Annotated[int, Field(strict=True, ge=1, le=5)]
    expected_revision: Annotated[int, Field(strict=True, ge=0)]
