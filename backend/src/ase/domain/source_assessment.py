"""Scoped qualitative assessments, with explicit authorship and immutable revisions.

These records do not authenticate an assessor. Application adapters must bind
reviewer identities to authorised actors and retain the cited review evidence.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ase.domain.events import Credibility, Reliability

ASSESSMENT_POLICY_VERSION = "ase-source-assessment-v1"


def assessment_text(value: object, maximum: int = 500) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or any(ord(char) < 32 and char not in "\n\r\t" for char in value)
    ):
        raise ValueError("Assessment text must be non-empty and within its bounds.")


def assessment_time(value: object) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Assessment dates require an explicit timezone.")


class Assessor(StrEnum):
    REVIEWER = "reviewer"
    POLICY = "policy"
    MODEL = "model"
    THIRD_PARTY = "third_party"
    LEGACY = "legacy"


class RatingStatus(StrEnum):
    APPLIED = "applied"
    PROPOSAL = "proposal"


class Authenticity(StrEnum):
    ESTABLISHED = "established"
    UNASSESSED = "unassessed"
    DISPUTED = "disputed"


@dataclass(frozen=True, slots=True)
class RatingReview:
    id: str
    assessor: Assessor
    assessor_id: str
    status: RatingStatus
    basis: str
    policy_version: str
    recorded_at: datetime
    reviewed_at: datetime | None = None
    supersedes: str | None = None
    policy_note: str | None = None

    def __post_init__(self) -> None:
        for value in (self.id, self.assessor_id, self.policy_version):
            assessment_text(value, 120)
        assessment_text(self.basis, 2000)
        assessment_time(self.recorded_at)
        if not isinstance(self.assessor, Assessor) or not isinstance(self.status, RatingStatus):
            raise ValueError("Unknown assessment author or status.")
        if self.assessor in (Assessor.MODEL, Assessor.THIRD_PARTY) and (
            self.status is RatingStatus.APPLIED
        ):
            raise ValueError("Model and third-party grades remain proposals until reviewed.")
        if self.reviewed_at is not None:
            assessment_time(self.reviewed_at)
            if self.assessor is not Assessor.REVIEWER or self.reviewed_at > self.recorded_at:
                raise ValueError("Only a recorded reviewer decision has a review date.")
        if self.assessor is Assessor.REVIEWER and self.reviewed_at is None:
            raise ValueError("Reviewer decisions require their actual review date.")
        if self.supersedes is not None:
            assessment_text(self.supersedes, 120)
            if self.supersedes == self.id:
                raise ValueError("An assessment cannot supersede itself.")
        if self.policy_note is not None:
            assessment_text(self.policy_note, 1000)


@dataclass(frozen=True, slots=True)
class SourceRatingRevision:
    source_id: str
    subject: str
    reliability: Reliability
    expertise_basis: str | None
    review: RatingReview

    def __post_init__(self) -> None:
        assessment_text(self.source_id, 120)
        assessment_text(self.subject, 200)
        if not isinstance(self.reliability, Reliability) or not isinstance(
            self.review, RatingReview
        ):
            raise ValueError("Source ratings require a qualitative grade and review record.")
        if self.expertise_basis is not None:
            assessment_text(self.expertise_basis, 1000)
        if (
            self.reliability is not Reliability.F
            and self.expertise_basis is None
            and (self.review.assessor is not Assessor.LEGACY or self.review.policy_note is None)
        ):
            raise ValueError("Unknown subject competence must retain reliability F.")


@dataclass(frozen=True, slots=True)
class AssertionRatingRevision:
    evidence_id: str
    claim_id: str
    credibility: Credibility
    review: RatingReview

    def __post_init__(self) -> None:
        assessment_text(self.evidence_id, 120)
        assessment_text(self.claim_id, 120)
        if not isinstance(self.credibility, Credibility) or not isinstance(
            self.review, RatingReview
        ):
            raise ValueError("Assertion ratings require a qualitative grade and review record.")


@dataclass(frozen=True, slots=True)
class IssuerAuthenticity:
    """Authenticity of one captured publication, never credibility of its assertion.

    An observed reference identifies a retained capture/authentication receipt;
    the policy does not infer authenticity from a URL or a government label.
    """

    evidence_id: str
    issuer_id: str
    status: Authenticity
    basis: str
    observed_reference: str | None = None

    def __post_init__(self) -> None:
        for value in (self.evidence_id, self.issuer_id):
            assessment_text(value, 120)
        assessment_text(self.basis, 1000)
        if not isinstance(self.status, Authenticity):
            raise ValueError("Unknown issuer-authenticity state.")
        if self.observed_reference is not None:
            assessment_text(self.observed_reference, 200)
        if self.status is not Authenticity.UNASSESSED and self.observed_reference is None:
            raise ValueError("An authenticity finding requires its observed reference.")


@dataclass(frozen=True, slots=True)
class ScopedSourceAssessment:
    evidence_id: str
    claim_id: str
    source_id: str
    subject: str
    reliability: Reliability
    credibility: Credibility
    source_revision: SourceRatingRevision | None
    assertion_revision: AssertionRatingRevision | None
    authenticity: IssuerAuthenticity | None
    review_notes: tuple[str, ...]
    policy_version: str = ASSESSMENT_POLICY_VERSION

    def __post_init__(self) -> None:
        for value in (self.evidence_id, self.claim_id, self.source_id, self.subject):
            assessment_text(value, 200)
        if self.policy_version != ASSESSMENT_POLICY_VERSION:
            raise ValueError("Unsupported source-assessment policy.")
        if not isinstance(self.reliability, Reliability) or not isinstance(
            self.credibility, Credibility
        ):
            raise ValueError("Assessments retain qualitative grades.")
        source, assertion = self.source_revision, self.assertion_revision
        if source is None:
            if self.reliability is not Reliability.F:
                raise ValueError("Source reliability needs an applied scoped revision.")
        elif (
            source.source_id != self.source_id
            or source.subject != self.subject
            or source.reliability is not self.reliability
            or source.review.status is not RatingStatus.APPLIED
        ):
            raise ValueError("The source revision does not match this assessment.")
        if assertion is None:
            if self.credibility is not Credibility.CANNOT_BE_JUDGED:
                raise ValueError("Assertion credibility needs an applied scoped revision.")
        elif (
            assertion.evidence_id != self.evidence_id
            or assertion.claim_id != self.claim_id
            or assertion.credibility is not self.credibility
            or assertion.review.status is not RatingStatus.APPLIED
        ):
            raise ValueError("The assertion revision does not match this assessment.")
        if self.authenticity is not None and (
            self.authenticity.evidence_id != self.evidence_id
            or self.authenticity.issuer_id != self.source_id
        ):
            raise ValueError("Issuer authenticity must match the captured publication.")
        if type(self.review_notes) is not tuple or len(self.review_notes) > 16:
            raise ValueError("Assessment review notes require a bounded immutable sequence.")
        for note in self.review_notes:
            assessment_text(note, 1000)
