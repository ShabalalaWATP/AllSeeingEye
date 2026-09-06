"""Frozen, non-secret model configuration provenance for one report version."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from ase.domain.llm import LlmRole, ReasoningEffort


@dataclass(frozen=True, slots=True)
class RoutedModel:
    role: LlmRole
    profile_id: UUID
    profile_revision: int
    model: str
    reasoning_effort: ReasoningEffort | None
    max_output_tokens: int
    temperature: float
    profile_updated_at: datetime


@dataclass(frozen=True, slots=True)
class ModelRoutingRecord:
    policy: Literal["legacy", "global", "team"]
    destination_team_id: UUID | None
    binding_team_id: UUID | None
    profiles: tuple[RoutedModel, ...]
