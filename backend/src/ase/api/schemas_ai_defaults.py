"""HTTP contracts for the suggested starting set of AI allowance policies."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from ase.api.schemas_ai_cost import AiTokenPricesOut
from ase.api.schemas_ai_usage import AiUsagePolicyOut, AiUsageTotalsOut
from ase.application.ai_usage_defaults import AiPolicyDefaults, SuggestedPolicy
from ase.domain.ai_pricing import AiTokenPrices
from ase.domain.ai_usage import AiAllowancePeriod, AiPolicyScope, AiUsagePolicy


class SuggestedPolicyOut(BaseModel):
    scope: AiPolicyScope
    target_id: UUID | None
    target_name: str
    period: AiAllowancePeriod
    token_limit: int
    reason: str
    already_configured: bool = Field(
        description="An enabled policy already covers this scope, target and period."
    )

    @classmethod
    def from_suggestion(cls, item: SuggestedPolicy) -> Self:
        return cls(
            scope=item.scope,
            target_id=item.target_id,
            target_name=item.target_name,
            period=item.period,
            token_limit=item.token_limit,
            reason=item.reason,
            already_configured=item.already_configured,
        )


class AiPolicyDefaultsOut(BaseModel):
    """What one click would create, beside the usage it is being compared against."""

    items: list[SuggestedPolicyOut]
    observed: AiUsageTotalsOut
    observed_daily_tokens: int = Field(
        description="Recorded tokens this month divided by the days elapsed."
    )
    enforcing: bool = Field(description="False while no enabled policy exists: nothing is capped.")
    prices: AiTokenPricesOut

    @classmethod
    def from_defaults(cls, defaults: AiPolicyDefaults, prices: AiTokenPrices) -> Self:
        return cls(
            items=[SuggestedPolicyOut.from_suggestion(item) for item in defaults.items],
            observed=AiUsageTotalsOut.from_totals(defaults.observed, prices),
            observed_daily_tokens=defaults.observed_daily_tokens,
            enforcing=defaults.any_policy_configured,
            prices=AiTokenPricesOut.from_prices(prices),
        )


class AppliedDefaultsOut(BaseModel):
    created: list[AiUsagePolicyOut]

    @classmethod
    def from_policies(cls, policies: list[AiUsagePolicy]) -> Self:
        return cls(created=[AiUsagePolicyOut.from_policy(policy) for policy in policies])
