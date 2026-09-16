"""HTTP contracts for estimated AI spend and the model a destination would use.

Prices are an operator setting used to turn recorded tokens into an approximate figure.
They are never a bill.  Model descriptions carry configuration only: no base URL, no key
and no key hint ever leaves the server through these contracts.
"""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field

from ase.domain.ai_pricing import AiTokenPrices
from ase.domain.llm import LlmProvider, ReasoningEffort
from ase.domain.model_routing import EffectiveModel


class AiTokenPricesOut(BaseModel):
    """Operator-configured prices used to estimate spend. Never a billing figure."""

    input_per_million: float
    output_per_million: float
    currency: str
    configured: bool = Field(
        description="False when both prices are zero, so no estimate is shown."
    )

    @classmethod
    def from_prices(cls, prices: AiTokenPrices) -> Self:
        return cls(
            input_per_million=float(prices.input_per_million),
            output_per_million=float(prices.output_per_million),
            currency=prices.currency,
            configured=prices.configured,
        )


class AiEffectiveModelOut(BaseModel):
    """The text model a person or team would use on their next call."""

    policy: Literal["legacy", "global", "team", "personal"] | None
    profile_id: UUID | None
    profile_name: str
    model: str
    provider: LlmProvider | None
    reasoning_effort: ReasoningEffort | None
    mechanical_effort: ReasoningEffort | None = Field(
        default=None, description="Effort mechanical work uses after the configured cap."
    )
    unavailable: str | None

    @classmethod
    def from_model(cls, model: EffectiveModel | None) -> Self | None:
        if model is None:
            return None
        return cls(
            policy=model.policy,
            profile_id=model.profile_id,
            profile_name=model.profile_name,
            model=model.model,
            provider=model.provider,
            reasoning_effort=model.reasoning_effort,
            mechanical_effort=model.mechanical_effort,
            unavailable=model.unavailable,
        )
