"""Typed frozen assessment and public methodology responses, separate from model output."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ase.domain.doctrine import Confidence, Probability
from ase.domain.evidence_matrix import Contribution


class EvidenceAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    label: str
    event_id: str
    source_id: str
    reliability: str
    credibility: int
    contribution: Contribution
    organisation: str | None
    flags: list[str]
    reasons: list[str]


class ContributionGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    labels: list[str]
    known_organisation: bool
    contribution: Contribution
    corroborating_contribution: Contribution
    possible_copy: bool
    confirmed_strong: bool


class JudgementAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    judgement_id: str
    supporting_labels: list[str]
    contradicting_labels: list[str]
    invalid_labels: list[str]
    support_groups: list[ContributionGroupOut]
    opposition_groups: list[ContributionGroupOut]
    support_tier: Contribution
    opposition_tier: Contribution
    balance: Literal[
        "no_support", "support_only", "support_stronger", "opposition_at_least_as_strong"
    ]
    status: Literal["supported", "limited", "contested", "unsupported"]
    confidence_ceiling: Confidence
    final_confidence: Confidence
    explanation: list[str]
    limitations: list[str]
    improvements: list[str]


class AssessmentTalliesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    evidence_items: int
    declared_groups: int
    unknown_provenance_items: int
    possible_copy_groups: int
    judgements: int
    strong: int
    moderate: int
    limited: int
    unassessed: int
    supported_judgements: int
    limited_judgements: int
    contested_judgements: int
    unsupported_judgements: int


class ReportAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    method_version: str
    evidence: list[EvidenceAssessmentOut]
    judgements: list[JudgementAssessmentOut]
    tallies: AssessmentTalliesOut
    validation_errors: int
    validation_warnings: int
    limitations: list[str]


class MatrixCellOut(BaseModel):
    reliability: str
    credibility: int
    contribution: Contribution


class ReliabilityLabelOut(BaseModel):
    grade: str
    label: str


class CredibilityLabelOut(BaseModel):
    grade: int
    label: str


class AssessmentDimensionOut(BaseModel):
    name: str
    engine_assessed: bool
    description: str


class DoctrineReferenceOut(BaseModel):
    title: str
    url: str


class YardstickBandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    probability: Probability
    term: str
    low_percent: int
    high_percent: int
    range_description: str


class ReportMethodologyOut(BaseModel):
    method_version: str
    title: str
    contribution_matrix: list[MatrixCellOut]
    reliability_scale: list[ReliabilityLabelOut]
    credibility_scale: list[CredibilityLabelOut]
    assessment_dimensions: list[AssessmentDimensionOut]
    confidence_rules: list[str]
    limitations: list[str]
    doctrine_references: list[DoctrineReferenceOut]
    probability_yardstick: list[YardstickBandOut]
