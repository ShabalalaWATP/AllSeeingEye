"""Request and response models for LLM profiles. Keys go in, only a hint ever comes out."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from ase.application.admin.llm import ProfileInput
from ase.application.admin.llm_connections import ConnectionInput
from ase.application.admin.llm_testing import TestOutcome
from ase.domain.llm import (
    MAX_API_KEY_LENGTH,
    MAX_MODEL_ID_LENGTH,
    MAX_OUTPUT_TOKENS,
    MIN_OUTPUT_TOKENS,
    LlmConnectionBinding,
    LlmProfile,
    LlmProvider,
    LlmRole,
    LlmUsage,
    ReasoningEffort,
    normalise_base_url,
)


class LlmProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    base_url: str = Field(min_length=8, max_length=512)
    model: str = Field(min_length=1, max_length=MAX_MODEL_ID_LENGTH)
    roles: list[LlmRole] = Field(default_factory=lambda: [LlmRole.ASSESSMENT])
    max_output_tokens: int = Field(default=4_000, ge=MIN_OUTPUT_TOKENS, le=MAX_OUTPUT_TOKENS)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    enabled: bool = False
    reasoning_effort: ReasoningEffort | None = None
    provider: LlmProvider = LlmProvider.OPENAI_COMPATIBLE
    # Blank on update keeps the stored key; on create an empty key means a keyless endpoint.
    api_key: SecretStr | None = Field(default=None, max_length=MAX_API_KEY_LENGTH)

    @field_validator("base_url")
    @classmethod
    def _absolute_http(cls, value: str) -> str:
        return normalise_base_url(value)

    def to_input(self) -> ProfileInput:
        key = self.api_key.get_secret_value().strip() if self.api_key else ""
        return ProfileInput(
            name=self.name,
            base_url=self.base_url,
            model=self.model,
            roles=frozenset(self.roles),
            max_output_tokens=self.max_output_tokens,
            temperature=self.temperature,
            enabled=self.enabled,
            api_key=key or None,
            reasoning_effort=self.reasoning_effort,
            provider=self.provider,
        )


class LlmProfileOut(BaseModel):
    id: UUID
    name: str
    base_url: str
    model: str
    api_key_hint: str
    roles: list[LlmRole]
    max_output_tokens: int
    temperature: float
    enabled: bool
    created_at: datetime
    updated_at: datetime
    reasoning_effort: ReasoningEffort | None
    provider: LlmProvider
    revision: int
    tested_at: datetime | None
    tested_revision: int | None
    tested_config_hash: str | None
    is_tested: bool
    is_bound: bool = False

    @classmethod
    def from_profile(cls, profile: LlmProfile, *, is_bound: bool = False) -> Self:
        return cls(
            id=profile.id,
            name=profile.name,
            base_url=profile.base_url,
            model=profile.model,
            api_key_hint=profile.api_key_hint,
            roles=sorted(profile.roles, key=lambda role: role.value),
            max_output_tokens=profile.max_output_tokens,
            temperature=profile.temperature,
            enabled=profile.enabled,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            reasoning_effort=profile.reasoning_effort,
            provider=profile.provider,
            revision=profile.revision,
            tested_at=profile.tested_at,
            tested_revision=profile.tested_revision,
            tested_config_hash=profile.tested_config_hash,
            is_tested=profile.is_tested,
            is_bound=is_bound,
        )


class LlmProfilesOut(BaseModel):
    items: list[LlmProfileOut]
    encryption_available: bool


class LlmTestOut(BaseModel):
    ok: bool
    latency_ms: float
    model: str | None
    error: str | None
    revision: int | None
    tested_at: datetime | None
    tested_config_hash: str | None

    @classmethod
    def from_outcome(cls, outcome: TestOutcome) -> Self:
        return cls(
            ok=outcome.ok,
            latency_ms=round(outcome.latency_ms, 1),
            model=outcome.model,
            error=outcome.error,
            revision=outcome.revision,
            tested_at=outcome.tested_at,
            tested_config_hash=outcome.tested_config_hash,
        )


class LlmUsageOut(BaseModel):
    id: int | None
    at: datetime
    profile_id: UUID
    user_id: UUID | None
    purpose: str
    ok: bool
    latency_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    error: str | None

    @classmethod
    def from_usage(cls, usage: LlmUsage) -> Self:
        return cls(
            id=usage.id,
            at=usage.at,
            profile_id=usage.profile_id,
            user_id=usage.user_id,
            purpose=usage.purpose,
            ok=usage.ok,
            latency_ms=round(usage.latency_ms, 1),
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            error=usage.error,
        )


class LlmUsagePageOut(BaseModel):
    items: list[LlmUsageOut]


class LlmModelsOut(BaseModel):
    models: list[str]


class LlmConnectionIn(BaseModel):
    user_id: UUID | None = None
    team_id: UUID | None = None
    profile_id: UUID
    expected_profile_revision: int = Field(ge=1)
    tested_config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_binding_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def one_audience(self) -> Self:
        if self.team_id is not None and self.user_id is not None:
            raise ValueError("Select either a team or a personal workspace.")
        return self

    def to_input(self) -> ConnectionInput:
        return ConnectionInput(
            self.team_id,
            self.profile_id,
            self.expected_profile_revision,
            self.tested_config_hash,
            self.expected_binding_revision,
            user_id=self.user_id,
        )


class LlmConnectionOut(BaseModel):
    user_id: UUID | None = None
    team_id: UUID | None
    profile_id: UUID
    profile_revision: int
    tested_config_hash: str
    activated_at: datetime
    activated_by: UUID
    revision: int

    @classmethod
    def from_binding(cls, binding: LlmConnectionBinding) -> Self:
        return cls(
            team_id=binding.team_id,
            user_id=binding.user_id,
            profile_id=binding.profile_id,
            profile_revision=binding.profile_revision,
            tested_config_hash=binding.tested_config_hash,
            activated_at=binding.activated_at,
            activated_by=binding.activated_by,
            revision=binding.revision,
        )


class LlmConnectionsOut(BaseModel):
    items: list[LlmConnectionOut]
