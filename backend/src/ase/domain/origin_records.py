"""Claim-scoped origin declarations and retained evidence for relationship proposals."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ase.domain.source_assessment import Assessor, assessment_text, assessment_time


class OriginRole(StrEnum):
    ORIGINAL_DOCUMENT = "original_document"
    ORIGINAL_STATEMENT = "original_statement"
    DIRECT_WITNESS = "direct_witness"
    DERIVED = "derived"
    UNKNOWN = "unknown"


class OriginRelation(StrEnum):
    REPUBLICATION = "republication"
    TRANSLATION = "translation"
    CITATION_CHAIN = "citation_chain"
    POSSIBLE_SHARED_ANONYMOUS_ORIGIN = "possible_shared_anonymous_origin"


class OriginStatus(StrEnum):
    PROPOSAL = "proposal"
    OBSERVED = "observed"
    REVIEWED = "reviewed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class OriginNode:
    id: str
    evidence_id: str
    claim_id: str
    source_id: str
    role: OriginRole
    organisation: str | None = None
    original_identity: str | None = None

    def __post_init__(self) -> None:
        for value in (self.id, self.evidence_id, self.claim_id, self.source_id):
            assessment_text(value, 120)
        for optional_value in (self.organisation, self.original_identity):
            if optional_value is not None:
                assessment_text(optional_value, 200)
        if not isinstance(self.role, OriginRole):
            raise ValueError("Unknown original-source role.")
        if self.role is OriginRole.UNKNOWN and self.original_identity is not None:
            raise ValueError("An unknown origin cannot assert an original identity.")


@dataclass(frozen=True, slots=True)
class OriginObservation:
    """An adapter-retained exact link or passage, not a model-invented reference.

    Pure code checks membership. Only a trusted capture/review adapter may set
    relation and target after observing that correspondence. A model proposal
    cannot populate this registry. A generic retained passage alone supports no
    particular relationship; neither state proves the underlying claim true.
    """

    id: str
    evidence_id: str
    kind: str
    reference: str
    relation: OriginRelation | None = None
    target_evidence_id: str | None = None
    claim_id: str | None = None

    def __post_init__(self) -> None:
        for value in (self.id, self.evidence_id):
            assessment_text(value, 120)
        if self.kind not in ("link", "passage"):
            raise ValueError("An origin observation must identify a retained link or passage.")
        assessment_text(self.reference, 2000)
        if (self.relation is None) != (self.target_evidence_id is None):
            raise ValueError("Observed relationships require both their kind and exact target.")
        if self.relation is not None:
            if not isinstance(self.relation, OriginRelation):
                raise ValueError("Unknown observed origin relationship.")
            assessment_text(self.target_evidence_id, 120)
            assessment_text(self.claim_id, 120)
            if self.target_evidence_id == self.evidence_id:
                raise ValueError("An observed origin relationship needs a different target.")
        if self.claim_id is not None:
            assessment_text(self.claim_id, 120)


@dataclass(frozen=True, slots=True)
class OriginEdge:
    id: str
    child_id: str
    parent_id: str
    relation: OriginRelation
    reason: str
    assessor: Assessor
    assessor_id: str
    method: str
    recorded_at: datetime
    observation_ids: tuple[str, ...] = ()
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
    rejected: bool = False

    def __post_init__(self) -> None:
        for value in (self.id, self.child_id, self.parent_id, self.assessor_id, self.method):
            assessment_text(value, 120)
        assessment_text(self.reason, 2000)
        assessment_time(self.recorded_at)
        if not isinstance(self.relation, OriginRelation) or not isinstance(self.assessor, Assessor):
            raise ValueError("Unknown origin relationship or assessor.")
        if self.child_id == self.parent_id:
            raise ValueError("An origin relationship must connect different records.")
        if type(self.observation_ids) is not tuple or len(self.observation_ids) > 16:
            raise ValueError("Origin observations require a bounded immutable sequence.")
        for value in self.observation_ids:
            assessment_text(value, 120)
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise ValueError("Repeated observations do not add relationship support.")
        if (self.reviewer_id is None) != (self.reviewed_at is None):
            raise ValueError("Origin review requires both an actor and actual review date.")
        if self.reviewer_id is not None:
            assessment_text(self.reviewer_id, 120)
            assessment_time(self.reviewed_at)
            if self.reviewed_at is not None and self.reviewed_at > self.recorded_at:
                raise ValueError("Origin review cannot postdate its recorded decision.")
        if type(self.rejected) is not bool or (self.rejected and self.reviewer_id is None):
            raise ValueError("Only a recorded reviewer decision can reject a proposed relation.")


@dataclass(frozen=True, slots=True)
class AssessedOriginEdge:
    edge: OriginEdge
    status: OriginStatus
    effective: bool


@dataclass(frozen=True, slots=True)
class OriginGroup:
    id: str
    claim_id: str
    member_ids: tuple[str, ...]
    known_original_ids: tuple[str, ...]
    review_required: bool
    reasons: tuple[str, ...]
