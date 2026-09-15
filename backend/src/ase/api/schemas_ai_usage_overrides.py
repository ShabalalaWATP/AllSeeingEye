"""HTTP contracts for dated temporary AI allowance overrides."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from ase.application.ai_usage_admin import AiOverrideInput
from ase.domain.ai_usage import MAX_ALLOWANCE
from ase.domain.ai_usage_overrides import AiLimitOverride, AiLimitState, AiPolicyOverride


class AiLimitOverrideIn(BaseModel):
    """``limit`` needs a value (zero blocks); other states must not carry one."""

    model_config = ConfigDict(extra="forbid")

    state: AiLimitState
    value: int | None = Field(default=None, ge=0, le=MAX_ALLOWANCE)

    @model_validator(mode="after")
    def value_matches_state(self) -> Self:
        if (self.state is AiLimitState.LIMIT) != (self.value is not None):
            raise ValueError("Only an explicit limit state carries a whole-number value.")
        return self

    def to_domain(self) -> AiLimitOverride:
        return AiLimitOverride(self.state, self.value)


class AiLimitOverrideOut(BaseModel):
    state: AiLimitState
    value: int | None

    @classmethod
    def from_domain(cls, value: AiLimitOverride) -> Self:
        return cls(state=value.state, value=value.value)


class AiPolicyOverrideIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requests: AiLimitOverrideIn
    tokens: AiLimitOverrideIn
    effective_from: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def window_is_ordered(self) -> Self:
        if self.expires_at <= self.effective_from:
            raise ValueError("An override must expire after it becomes effective.")
        return self

    def to_input(self) -> AiOverrideInput:
        return AiOverrideInput(
            self.requests.to_domain(),
            self.tokens.to_domain(),
            self.effective_from,
            self.expires_at,
        )


class AiPolicyOverrideOut(BaseModel):
    id: UUID
    policy_id: UUID
    requests: AiLimitOverrideOut
    tokens: AiLimitOverrideOut
    effective_from: datetime
    expires_at: datetime
    created_by: UUID
    created_at: datetime
    revoked_at: datetime | None

    @classmethod
    def from_override(cls, override: AiPolicyOverride) -> Self:
        return cls(
            id=override.id,
            policy_id=override.policy_id,
            requests=AiLimitOverrideOut.from_domain(override.requests),
            tokens=AiLimitOverrideOut.from_domain(override.tokens),
            effective_from=override.effective_from,
            expires_at=override.expires_at,
            created_by=override.created_by,
            created_at=override.created_at,
            revoked_at=override.revoked_at,
        )


class AiPolicyOverridesOut(BaseModel):
    items: list[AiPolicyOverrideOut]
