"""HTTP contracts for AI allowances and account-visible usage summaries."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.application.ai_usage import AiPolicyInput
from ase.domain.ai_usage import (
    MAX_ALLOWANCE,
    AiAllowancePeriod,
    AiPolicyScope,
    AiUsagePolicy,
    AiUsageReservation,
    AiUsageSummary,
)


class AiUsagePolicyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: AiPolicyScope
    target_id: UUID | None = None
    period: AiAllowancePeriod = AiAllowancePeriod.MONTH
    request_limit: int | None = Field(default=None, ge=0, le=MAX_ALLOWANCE)
    token_limit: int | None = Field(default=None, ge=0, le=MAX_ALLOWANCE)
    enabled: bool = True

    @model_validator(mode="after")
    def target_matches_scope(self) -> Self:
        if self.scope is AiPolicyScope.GLOBAL and self.target_id is not None:
            raise ValueError("A global policy cannot have a target id.")
        if self.scope is not AiPolicyScope.GLOBAL and self.target_id is None:
            raise ValueError("A user or team policy needs a target id.")
        return self

    def to_input(self) -> AiPolicyInput:
        return AiPolicyInput(
            self.scope,
            self.target_id,
            self.period,
            self.request_limit,
            self.token_limit,
            self.enabled,
        )


class AiUsagePolicyOut(BaseModel):
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

    @classmethod
    def from_policy(cls, policy: AiUsagePolicy) -> Self:
        return cls(
            id=policy.id,
            scope=policy.scope,
            target_id=policy.target_id,
            period=policy.period,
            request_limit=policy.request_limit,
            token_limit=policy.token_limit,
            enabled=policy.enabled,
            revision=policy.revision,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )


class AiUsageSummaryOut(BaseModel):
    policy: AiUsagePolicyOut
    period_start: datetime
    period_end: datetime
    used_requests: int
    reserved_requests: int
    remaining_requests: int | None
    used_tokens: int
    reserved_tokens: int
    remaining_tokens: int | None

    @classmethod
    def from_summary(cls, summary: AiUsageSummary) -> Self:
        return cls(
            policy=AiUsagePolicyOut.from_policy(summary.policy),
            period_start=summary.period_start,
            period_end=summary.period_end,
            used_requests=summary.used_requests,
            reserved_requests=summary.reserved_requests,
            remaining_requests=summary.remaining_requests,
            used_tokens=summary.used_tokens,
            reserved_tokens=summary.reserved_tokens,
            remaining_tokens=summary.remaining_tokens,
        )


class AiUsageSummaryPageOut(BaseModel):
    items: list[AiUsageSummaryOut]


class AiUsageReservationOut(BaseModel):
    id: UUID
    policy_id: UUID
    user_id: UUID
    profile_id: UUID | None
    model: str
    purpose: str
    period_start: datetime
    period_end: datetime
    reserved_tokens: int
    status: str
    created_at: datetime
    settled_at: datetime | None
    prompt_tokens: int | None
    completion_tokens: int | None
    actual_tokens: int | None
    ok: bool | None
    error: str | None

    @classmethod
    def from_reservation(cls, reservation: AiUsageReservation) -> Self:
        return cls(
            id=reservation.id,
            policy_id=reservation.policy_id,
            user_id=reservation.user_id,
            profile_id=reservation.profile_id,
            model=reservation.model,
            purpose=reservation.purpose,
            period_start=reservation.period_start,
            period_end=reservation.period_end,
            reserved_tokens=reservation.reserved_tokens,
            status=reservation.status.value,
            created_at=reservation.created_at,
            settled_at=reservation.settled_at,
            prompt_tokens=reservation.prompt_tokens,
            completion_tokens=reservation.completion_tokens,
            actual_tokens=reservation.actual_tokens,
            ok=reservation.ok,
            error=reservation.error,
        )


class AiUsageReservationsOut(BaseModel):
    items: list[AiUsageReservationOut]
