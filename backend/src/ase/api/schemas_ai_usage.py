"""HTTP contracts for AI allowances and account-visible usage summaries."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.api.schemas_ai_cost import AiEffectiveModelOut, AiTokenPricesOut
from ase.api.schemas_ai_usage_overrides import AiPolicyOverrideOut
from ase.application.ai_usage_admin import AiPolicyInput
from ase.application.ai_usage_views import AccountAiUsage, AiUsagePreview, TeamAiUsage
from ase.domain.ai_pricing import AiTokenPrices
from ase.domain.ai_usage import (
    MAX_ALLOWANCE,
    UNTARGETED_SCOPES,
    AiAllowancePeriod,
    AiMemberUsage,
    AiPolicyScope,
    AiUsagePolicy,
    AiUsageReservation,
    AiUsageSummary,
    AiUsageTotals,
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
        if self.scope in UNTARGETED_SCOPES and self.target_id is not None:
            raise ValueError("A site or system policy cannot have a target id.")
        if self.scope not in UNTARGETED_SCOPES and self.target_id is None:
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
    request_limit: int | None = Field(description="Effective limit after any active override.")
    token_limit: int | None = Field(description="Effective limit after any active override.")
    override: AiPolicyOverrideOut | None
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
            request_limit=summary.request_limit,
            token_limit=summary.token_limit,
            override=AiPolicyOverrideOut.from_override(summary.override)
            if summary.override
            else None,
            used_requests=summary.used_requests,
            reserved_requests=summary.reserved_requests,
            remaining_requests=summary.remaining_requests,
            used_tokens=summary.used_tokens,
            reserved_tokens=summary.reserved_tokens,
            remaining_tokens=summary.remaining_tokens,
        )


class AiUsageTotalsOut(BaseModel):
    """Observed usage this UTC calendar month, whether or not a limit is configured."""

    period_start: datetime
    period_end: datetime
    used_requests: int
    used_tokens: int
    unknown_requests: int
    used_input_tokens: int
    used_output_tokens: int
    estimated_cost: str | None = Field(
        default=None,
        description="Estimated spend from recorded tokens at the configured prices.",
    )

    @classmethod
    def from_totals(cls, totals: AiUsageTotals, prices: AiTokenPrices | None = None) -> Self:
        cost = (
            prices.estimate(totals.used_input_tokens, totals.used_output_tokens)
            if prices is not None
            else None
        )
        return cls(
            period_start=totals.period_start,
            period_end=totals.period_end,
            used_requests=totals.used_requests,
            used_tokens=totals.used_tokens,
            unknown_requests=totals.unknown_requests,
            used_input_tokens=totals.used_input_tokens,
            used_output_tokens=totals.used_output_tokens,
            estimated_cost=None if cost is None else f"{cost}",
        )


def _summaries(items: list[AiUsageSummary]) -> list[AiUsageSummaryOut]:
    return [AiUsageSummaryOut.from_summary(item) for item in items]


class AiUsageSummaryPageOut(BaseModel):
    items: list[AiUsageSummaryOut]
    observed: AiUsageTotalsOut
    prices: AiTokenPricesOut

    @classmethod
    def from_account(cls, usage: AccountAiUsage, prices: AiTokenPrices) -> Self:
        return cls(
            items=_summaries(usage.summaries),
            observed=AiUsageTotalsOut.from_totals(usage.totals, prices),
            prices=AiTokenPricesOut.from_prices(prices),
        )


class AiUsagePreviewOut(BaseModel):
    items: list[AiUsageSummaryOut]
    observed: AiUsageTotalsOut
    unknown_calls: int = Field(description="Provider calls held as unknown pending review.")
    prices: AiTokenPricesOut
    model: AiEffectiveModelOut | None = Field(
        default=None, description="The model this destination would use. Never a credential."
    )

    @classmethod
    def from_preview(cls, preview: AiUsagePreview, prices: AiTokenPrices) -> Self:
        return cls(
            items=_summaries(preview.summaries),
            observed=AiUsageTotalsOut.from_totals(preview.totals, prices),
            unknown_calls=preview.unknown_calls,
            prices=AiTokenPricesOut.from_prices(prices),
            model=AiEffectiveModelOut.from_model(preview.model),
        )


class AiMemberUsageOut(BaseModel):
    user_id: UUID
    display_name: str
    observed: AiUsageTotalsOut

    @classmethod
    def from_member(cls, member: AiMemberUsage, prices: AiTokenPrices) -> Self:
        return cls(
            user_id=member.user_id,
            display_name=member.display_name,
            observed=AiUsageTotalsOut.from_totals(member.totals, prices),
        )


class TeamAiUsageOut(BaseModel):
    team_id: UUID
    view: Literal["member", "manager", "admin"]
    items: list[AiUsageSummaryOut]
    own: AiUsageTotalsOut
    team: AiUsageTotalsOut | None
    members: list[AiMemberUsageOut] | None
    prices: AiTokenPricesOut

    @classmethod
    def from_usage(cls, usage: TeamAiUsage, prices: AiTokenPrices) -> Self:
        return cls(
            team_id=usage.team_id,
            view=usage.view,
            items=_summaries(usage.summaries),
            own=AiUsageTotalsOut.from_totals(usage.own, prices),
            team=AiUsageTotalsOut.from_totals(usage.team, prices) if usage.team else None,
            members=[AiMemberUsageOut.from_member(item, prices) for item in usage.members]
            if usage.members is not None
            else None,
            prices=AiTokenPricesOut.from_prices(prices),
        )


class AiUsageReservationOut(BaseModel):
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
    status: str
    created_at: datetime
    dispatched_at: datetime | None
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
            call_id=reservation.call_id,
            policy_id=reservation.policy_id,
            user_id=reservation.user_id,
            team_id=reservation.team_id,
            system=reservation.system,
            profile_id=reservation.profile_id,
            model=reservation.model,
            purpose=reservation.purpose,
            period_start=reservation.period_start,
            period_end=reservation.period_end,
            reserved_tokens=reservation.reserved_tokens,
            status=reservation.status.value,
            created_at=reservation.created_at,
            dispatched_at=reservation.dispatched_at,
            settled_at=reservation.settled_at,
            prompt_tokens=reservation.prompt_tokens,
            completion_tokens=reservation.completion_tokens,
            actual_tokens=reservation.actual_tokens,
            ok=reservation.ok,
            error=reservation.error,
        )


class AiUsageReservationsOut(BaseModel):
    items: list[AiUsageReservationOut]
