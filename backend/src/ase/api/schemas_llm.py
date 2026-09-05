"""Request and response models for LLM profiles. Keys go in, only a hint ever comes out."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator

from ase.application.admin.llm import ProfileInput, TestOutcome
from ase.domain.llm import (
    MAX_OUTPUT_TOKENS,
    MIN_OUTPUT_TOKENS,
    LlmProfile,
    LlmRole,
    LlmUsage,
    normalise_base_url,
)


class LlmProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    base_url: str = Field(min_length=8, max_length=512)
    model: str = Field(min_length=1, max_length=120)
    roles: list[LlmRole] = Field(default_factory=lambda: [LlmRole.ASSESSMENT])
    max_output_tokens: int = Field(default=4_000, ge=MIN_OUTPUT_TOKENS, le=MAX_OUTPUT_TOKENS)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    enabled: bool = True
    # Blank on update keeps the stored key; on create an empty key means a keyless endpoint.
    api_key: SecretStr | None = Field(default=None, max_length=512)

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

    @classmethod
    def from_profile(cls, profile: LlmProfile) -> Self:
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
        )


class LlmProfilesOut(BaseModel):
    items: list[LlmProfileOut]
    encryption_available: bool


class LlmTestOut(BaseModel):
    ok: bool
    latency_ms: float
    model: str | None
    error: str | None

    @classmethod
    def from_outcome(cls, outcome: TestOutcome) -> Self:
        return cls(
            ok=outcome.ok,
            latency_ms=round(outcome.latency_ms, 1),
            model=outcome.model,
            error=outcome.error,
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
