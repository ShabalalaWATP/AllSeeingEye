"""Strict, versioned resource schema for editable curated Research Brief starters."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ase.domain.research import ResearchMode
from ase.domain.research_brief_values import LensId

PresetGroup = Literal["conflict", "cyber", "economy", "cross_cutting"]
StableId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")]
ShortText = Annotated[str, Field(min_length=1, max_length=300)]
COMMON_SECTIONS = (
    "key_judgements",
    "supporting_findings",
    "opposing_evidence",
    "gaps",
    "references",
)
LENS_RULE = (
    "A lens changes relevance, audience and decision context only. Examine counterevidence "
    "and alternative explanations; source grades and likelihood rules do not change. "
    "Actor-perspective analysis examines stated aims, constraints and claims without endorsing "
    "them or directing a preferred factual conclusion."
)


class PresetModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PresetRequirement(PresetModel):
    id: StableId
    question: str = Field(min_length=1, max_length=500)
    required: bool = True
    priority: int = Field(ge=1, le=12)


class PresetInput(PresetModel):
    id: StableId
    label: ShortText
    guidance: str = Field(min_length=1, max_length=500)
    target: StableId
    required: bool = True


class PresetIndicator(PresetModel):
    id: StableId
    condition: str = Field(min_length=1, max_length=500)


class ResearchPreset(PresetModel):
    id: StableId
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=120)
    purpose: ShortText
    group: PresetGroup
    owner_role: str = Field(min_length=1, max_length=120)
    reviewed_on: date
    question: str = Field(min_length=1, max_length=2000)
    requirements: tuple[PresetRequirement, ...] = Field(min_length=1, max_length=6)
    required_inputs: tuple[PresetInput, ...] = Field(default=(), max_length=8)
    country_isos: tuple[Annotated[str, Field(pattern=r"^[A-Z]{2}$")], ...] = Field(
        default=(), max_length=8
    )
    scope_note: str = Field(min_length=1, max_length=600)
    suggested_languages: tuple[Annotated[str, Field(pattern=r"^[a-z]{2,3}$")], ...] = Field(
        min_length=1, max_length=8
    )
    language_note: str = Field(min_length=1, max_length=500)
    source_bundles: tuple[StableId, ...] = Field(min_length=1, max_length=13)
    optional_bundles: tuple[StableId, ...] = Field(default=(), max_length=13)
    source_ids: tuple[StableId, ...] = Field(default=(), max_length=64)
    declared_gap_ids: tuple[StableId, ...] = Field(default=(), max_length=16)
    lens_choices: tuple[LensId, ...] = Field(min_length=1, max_length=9)
    default_lens: LensId
    lens_note: str = Field(default=LENS_RULE, min_length=1, max_length=1000)
    default_depth: Literal[ResearchMode.DETAILED] = ResearchMode.DETAILED
    baseline_days: Literal[7] = 7
    forecast_horizon_days: Literal[30] | None = None
    sections: tuple[StableId, ...] = Field(min_length=5, max_length=16)
    indicators: tuple[PresetIndicator, ...] = Field(min_length=1, max_length=12)
    exclusions: tuple[ShortText, ...] = Field(min_length=1, max_length=10)
    quality_trap: str = Field(min_length=1, max_length=600)
    keywords: tuple[ShortText, ...] = Field(min_length=1, max_length=20)

    @field_validator("title", "purpose", "question", "scope_note", "quality_trap")
    @classmethod
    def plain_text(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 or char in "<>" for char in value):
            raise ValueError("Preset text must be plain, non-empty text")
        return value

    @model_validator(mode="after")
    def consistent(self) -> Self:
        for field in (
            "country_isos",
            "suggested_languages",
            "source_bundles",
            "optional_bundles",
            "source_ids",
            "declared_gap_ids",
            "lens_choices",
            "sections",
            "keywords",
        ):
            values = getattr(self, field)
            if len(set(values)) != len(values):
                raise ValueError("Preset choices must be unique")
        for values in (self.requirements, self.required_inputs, self.indicators):
            if len({row.id for row in values}) != len(values):
                raise ValueError("Preset item identifiers must be unique")
        if self.default_lens not in self.lens_choices or not set(COMMON_SECTIONS) <= set(
            self.sections
        ):
            raise ValueError("Preset needs its default lens and common evidence sections")
        if set(self.optional_bundles) & set(self.source_bundles):
            raise ValueError("Required and optional bundles must be distinct")
        if not all(key.startswith("gap.") for key in self.declared_gap_ids):
            raise ValueError("Declared coverage gaps use the gap namespace")
        if self.lens_note != LENS_RULE:
            raise ValueError("Presets must retain the shared impartial lens rule")
        return self


class PresetResource(PresetModel):
    schema_version: Literal[1]
    presets: tuple[ResearchPreset, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({row.id for row in self.presets}) != len(self.presets):
            raise ValueError("Preset IDs must be unique")
        return self
