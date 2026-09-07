"""Exact comparison artefacts, with operator correspondence kept separate from source facts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from ase.domain.claim_revisions import ClaimRevision
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_matrix import ReportAssessment
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.relationship_review import RelationshipReviewRevision
from ase.domain.reports import KeyJudgement

COMPARISON_METHOD = "ase-annotation-comparison-v1"
AnnotationKind = Literal["claim", "identity", "relationship"]
ChangeStatus = Literal["unchanged", "changed", "added", "removed"]
LIMITATIONS = (
    "This compares explicitly selected frozen revisions, not a complete annotation inventory.",
    "Different roots remain distinct unless an operator explicitly declares correspondence. "
    "Correspondence is not verified claim, identity or ownership equivalence.",
    "Unique identical judgement statements may correspond; reused judgement IDs alone do not. "
    "Unmatched judgements have separate assessments, not a directional confidence change.",
    "Reliability, information credibility and confidence are separate recorded dimensions. "
    "Observed differences do not establish unique causation or a probability of factual truth.",
    "Frozen assessments are not recomputed. Method-version differences may limit comparability.",
    "Removed evidence may reflect a collection window; it does not establish withdrawal. "
    "Publication, observation, capture, review and generated timestamps have distinct meanings.",
    "Generated-at is the server response time, not a trusted source observation timestamp.",
)


@dataclass(frozen=True, slots=True)
class AnnotationCorrespondence:
    kind: AnnotationKind
    before_revision_id: UUID
    after_revision_id: UUID
    rationale: str


@dataclass(frozen=True, slots=True)
class JudgementCorrespondence:
    before_judgement_id: str
    after_judgement_id: str
    rationale: str


@dataclass(frozen=True, slots=True)
class ComparisonSide:
    report_id: UUID
    version_id: UUID
    version_number: int
    title: str
    period_from: datetime | None
    period_to: datetime | None
    version_created_at: datetime
    data_cutoff: datetime | None
    evidence_sha256: str
    content_sha256: str
    revisions: tuple[ClaimRevision, ...]
    identity_revisions: tuple[IdentityDecisionRevision, ...]
    relationship_revisions: tuple[RelationshipReviewRevision, ...]
    evidence: tuple[EvidenceItem, ...]
    judgements: tuple[KeyJudgement, ...]
    assessment: ReportAssessment | None


@dataclass(frozen=True, slots=True)
class AnnotationChange:
    kind: AnnotationKind
    before_revision_id: UUID | None
    after_revision_id: UUID | None
    correspondence: Literal["same_root", "operator_declared", "unmatched"]
    status: ChangeStatus
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ComparisonEvidenceChange:
    source_id: str
    event_id: str
    before_label: str | None
    after_label: str | None
    status: ChangeStatus
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfidenceChange:
    before_judgement_id: str | None
    after_judgement_id: str | None
    correspondence: Literal["exact_statement", "operator_declared", "unmatched"]
    status: ChangeStatus
    changed_fields: tuple[str, ...]
    explanations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnnotationComparison:
    method_version: str
    generated_at: datetime
    comparison_sha256: str
    compared_by: UUID
    before: ComparisonSide
    after: ComparisonSide
    correspondences: tuple[AnnotationCorrespondence, ...]
    judgement_correspondences: tuple[JudgementCorrespondence, ...]
    annotation_changes: tuple[AnnotationChange, ...]
    evidence_changes: tuple[ComparisonEvidenceChange, ...]
    confidence_changes: tuple[ConfidenceChange, ...]
    limitations: tuple[str, ...] = LIMITATIONS
