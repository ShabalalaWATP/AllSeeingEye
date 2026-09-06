"""Read-only claim inspection derived from the authorised frozen report version."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ase.api.schemas_citation_checks import JudgementCitationCheckOut
from ase.api.schemas_report_assessment import JudgementAssessmentOut


class ClaimDimensionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: Literal["evidence_support", "source_independence", "coverage", "citation_validity"]
    status: str
    explanation: str


class ClaimSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    label: str
    relation: Literal["supporting", "contradicting"]
    evidence_id: str | None
    source_name: str | None
    organisation: str | None
    content_hash: str | None


class LedgerClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    judgement_id: str
    statement: str
    kind: Literal["analytical_inference"]
    confidence_statement: str
    assumptions: list[str]
    sources: list[ClaimSourceOut]
    assessment: JudgementAssessmentOut | None
    citation_checks: JudgementCitationCheckOut | None
    dimensions: list[ClaimDimensionOut]


class ClaimLedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    derivation_version: str
    report_version: int
    claims: list[LedgerClaimOut]
    recorded_gaps: list[str]
    limitations: list[str]
