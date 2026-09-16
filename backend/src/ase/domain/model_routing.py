"""Frozen, non-secret model configuration provenance for one report version."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from ase.domain.llm import LlmProvider, LlmRole, ReasoningEffort


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
    provider: LlmProvider = LlmProvider.OPENAI_COMPATIBLE


@dataclass(frozen=True, slots=True)
class ModelRoutingRecord:
    policy: Literal["legacy", "global", "team", "personal"]
    destination_team_id: UUID | None
    binding_team_id: UUID | None
    profiles: tuple[RoutedModel, ...]
    binding_user_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class EffectiveModel:
    """What a destination's next text call would use, or why it could not make one.

    Non-secret configuration only: no base URL, no key and no key hint. ``unavailable``
    carries the routing reason when no usable connection is assigned.
    """

    policy: Literal["legacy", "global", "team", "personal"] | None = None
    profile_id: UUID | None = None
    profile_name: str = ""
    model: str = ""
    provider: LlmProvider | None = None
    reasoning_effort: ReasoningEffort | None = None
    mechanical_effort: ReasoningEffort | None = None
    unavailable: str | None = None
