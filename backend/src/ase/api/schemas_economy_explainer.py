"""Explainer DTOs: written text plus the provenance a reader needs to judge it."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.economy_explainer import (
    GLOSSARY_ENTRIES,
    MAX_PLAIN_ENGLISH,
    MAX_TAKEAWAY,
    MAX_TERM,
    ExplainerStatus,
    ExplainerView,
)

WRITTEN_BY = (
    "Written by the model from the figures shown on this page. The figures are the "
    "source of truth; the words are a plain-English description of them."
)


class ExplainerSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    takeaway: str = Field(max_length=MAX_TAKEAWAY)
    paragraphs: list[str] = Field(max_length=3)
    drivers: list[str] = Field(max_length=4)
    watch: list[str] = Field(max_length=4)


class GlossaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    term: str = Field(max_length=MAX_TERM)
    plain_english: str = Field(max_length=MAX_PLAIN_ENGLISH)


class ExplainerRegionOut(BaseModel):
    id: str = Field(max_length=8)
    section: ExplainerSectionOut


class ExplainerBodyOut(BaseModel):
    world: ExplainerSectionOut
    regions: list[ExplainerRegionOut] = Field(max_length=5)
    glossary: list[GlossaryEntryOut] = Field(max_length=GLOSSARY_ENTRIES[1])


class ExplainerProvenanceOut(BaseModel):
    model: str = Field(max_length=255)
    generated_at: datetime
    snapshot_fetched_at: datetime
    prompt_tokens: int | None
    completion_tokens: int | None
    sources: list[str] = Field(max_length=6)
    written_by: str = WRITTEN_BY


class EconomyExplainerOut(BaseModel):
    status: ExplainerStatus
    stale: bool
    reason: str | None = Field(max_length=400)
    explainer: ExplainerBodyOut | None
    provenance: ExplainerProvenanceOut | None


def explainer_out(view: ExplainerView) -> EconomyExplainerOut:
    stored = view.explainer
    body = (
        ExplainerBodyOut(
            world=ExplainerSectionOut.model_validate(stored.text.world),
            regions=[
                ExplainerRegionOut(id=key, section=ExplainerSectionOut.model_validate(section))
                for key, section in stored.text.regions
            ],
            glossary=[GlossaryEntryOut.model_validate(entry) for entry in stored.text.glossary],
        )
        if stored is not None
        else None
    )
    provenance = (
        ExplainerProvenanceOut(
            model=stored.model,
            generated_at=stored.generated_at,
            snapshot_fetched_at=stored.snapshot_fetched_at,
            prompt_tokens=stored.prompt_tokens,
            completion_tokens=stored.completion_tokens,
            sources=list(view.sources),
        )
        if stored is not None
        else None
    )
    return EconomyExplainerOut(
        status=view.status,
        stale=view.stale,
        reason=view.reason,
        explainer=body,
        provenance=provenance,
    )
