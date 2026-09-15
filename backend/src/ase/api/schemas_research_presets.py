"""Discoverable preset and editable-definition contracts for the shared brief picker."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ase.api.schemas_research_briefs import ResearchBriefDraftIn
from ase.application.research.presets_readiness import PresetReadiness
from ase.application.research.presets_schema import LENS_RULE, ResearchPreset
from ase.domain.research import ResearchMode
from ase.domain.research_brief_values import LensId

_SelectionId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")]


class ResearchPresetOut(BaseModel):
    preset: ResearchPreset
    readiness: PresetReadiness


class ResearchPresetsOut(BaseModel):
    schema_version: int = 1
    items: list[ResearchPresetOut]
    lens_choices: list[LensId] = Field(default_factory=lambda: list(LensId))
    lens_rule: str = LENS_RULE


class PresetDefinitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, strict=True)
    depth: ResearchMode = ResearchMode.DETAILED
    lens: LensId | None = None
    selected_requirement_ids: tuple[_SelectionId, ...] | None = Field(
        default=None, min_length=1, max_length=6
    )
    selected_source_ids: tuple[_SelectionId, ...] | None = Field(default=None, max_length=64)


class PresetDefinitionOut(BaseModel):
    definition: ResearchBriefDraftIn
    readiness: PresetReadiness
    omitted_requirement_ids: list[str]
    note: str = (
        "Editable starter only; no brief was saved and no source was queried. Complete the "
        "required inputs and review coverage before admission. Save through the existing "
        "Research Brief endpoint to assign current ownership and preserve this preset version."
    )
