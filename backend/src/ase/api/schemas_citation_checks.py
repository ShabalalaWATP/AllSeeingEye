"""Typed literal citation checks, distinct from claim verification and evidence strength."""

from pydantic import BaseModel, ConfigDict

from ase.domain.citation_checks import CitationStatus, IndicatorKind, Relation, SourceField


class FrozenExcerptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    field: SourceField
    start: int
    end: int
    text: str
    sha256: str


class MismatchIndicatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: IndicatorKind
    claim_values: list[str]
    excerpt_values: list[str]
    explanation: str


class CitationCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    label: str
    relation: Relation
    status: CitationStatus
    evidence_id: str | None
    source_content_hash: str | None
    excerpt: FrozenExcerptOut | None
    indicators: list[MismatchIndicatorOut]
    reasons: list[str]


class JudgementCitationCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    judgement_id: str
    status: CitationStatus
    citations: list[CitationCheckOut]
    reasons: list[str]


class ReportCitationChecksOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    method_version: str
    judgements: list[JudgementCitationCheckOut]
    limitations: list[str]
