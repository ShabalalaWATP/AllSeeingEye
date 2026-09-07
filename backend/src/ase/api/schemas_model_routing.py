"""Historical model settings, without provider endpoints or credentials."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.llm import MAX_MODEL_ID_LENGTH, LlmProvider, LlmRole, ReasoningEffort


class RoutedModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: LlmRole
    profile_id: UUID
    profile_revision: int
    model: str = Field(max_length=MAX_MODEL_ID_LENGTH)
    provider: LlmProvider
    reasoning_effort: ReasoningEffort | None
    max_output_tokens: int
    temperature: float
    profile_updated_at: datetime


class ModelRoutingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    policy: Literal["legacy", "global", "team", "personal"]
    destination_team_id: UUID | None
    binding_team_id: UUID | None
    binding_user_id: UUID | None = None
    profiles: list[RoutedModelOut]
