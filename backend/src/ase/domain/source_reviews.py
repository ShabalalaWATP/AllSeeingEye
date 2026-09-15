"""Reviewer-authored policy history, separate from immutable report evidence."""

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from ase.domain.events import Credibility, Reliability
from ase.domain.source_assessment import (
    AssertionRatingRevision,
    Assessor,
    IssuerAuthenticity,
    RatingReview,
    RatingStatus,
    SourceRatingRevision,
    assessment_text,
)

MAX_SOURCE_REVIEW_HISTORY = 100
MAX_SCOPE_REVIEW_BYTES = 32 * 1024 * 1024
MAX_SCOPE_REVIEW_HEADS = 1000
MAX_VERSION_SOURCE_SNAPSHOTS = 20


class SourceReviewKind(StrEnum):
    RELIABILITY = "reliability"
    CREDIBILITY = "credibility"
    AUTHENTICITY = "authenticity"


@dataclass(frozen=True, slots=True)
class SourceReviewScope:
    owner_id: UUID
    team_id: UUID | None

    def __post_init__(self) -> None:
        if not isinstance(self.owner_id, UUID) or (
            self.team_id is not None and not isinstance(self.team_id, UUID)
        ):
            raise ValueError("Source reviews require an explicit personal or team scope.")


@dataclass(frozen=True, slots=True)
class SourceReviewTarget:
    report_id: UUID
    report_version_id: UUID
    source_id: str
    subject: str
    capture_id: str
    claim_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, UUID) or not isinstance(self.report_version_id, UUID):
            raise ValueError("Source reviews require an exact report version anchor.")
        for value in (self.source_id, self.subject, self.capture_id, self.claim_id):
            assessment_text(value, 200)


def source_review_key(
    scope: SourceReviewScope, kind: SourceReviewKind, target: SourceReviewTarget
) -> str:
    if not isinstance(kind, SourceReviewKind):
        raise ValueError("Unsupported source review kind.")
    anchor = (
        (target.source_id, target.subject)
        if kind is SourceReviewKind.RELIABILITY
        else (target.capture_id, target.claim_id)
        if kind is SourceReviewKind.CREDIBILITY
        else (target.capture_id, target.source_id)
    )
    tenant = f"team:{scope.team_id}" if scope.team_id is not None else f"owner:{scope.owner_id}"
    return hashlib.sha256(json.dumps((tenant, kind.value, anchor)).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceReviewRevision:
    scope: SourceReviewScope
    target: SourceReviewTarget
    kind: SourceReviewKind
    number: int
    review: RatingReview
    reliability: Reliability | None = None
    expertise_basis: str | None = None
    credibility: Credibility | None = None
    authenticity: IssuerAuthenticity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, SourceReviewScope) or not isinstance(
            self.target, SourceReviewTarget
        ):
            raise ValueError("Source review scope and target must be explicit.")
        if type(self.number) is not int or not 1 <= self.number <= MAX_SOURCE_REVIEW_HISTORY:
            raise ValueError("Source review history exceeds its retained revision limit.")
        if (
            not isinstance(self.review, RatingReview)
            or self.review.assessor is not Assessor.REVIEWER
            or self.review.status is not RatingStatus.APPLIED
            or (self.review.supersedes is None) != (self.number == 1)
        ):
            raise ValueError("Only attributed, applied reviewer decisions belong in this store.")
        UUID(self.review.id)
        UUID(self.review.assessor_id)
        if self.review.supersedes is not None:
            UUID(self.review.supersedes)
        if self.kind is SourceReviewKind.RELIABILITY:
            if (
                self.reliability is None
                or self.credibility is not None
                or self.authenticity is not None
            ):
                raise ValueError("Reliability decisions must retain their own qualitative axis.")
            self.source_revision()
        elif self.kind is SourceReviewKind.CREDIBILITY:
            if (
                self.credibility is None
                or self.reliability is not None
                or self.expertise_basis is not None
                or self.authenticity is not None
            ):
                raise ValueError("Credibility decisions must address only the captured assertion.")
            self.assertion_revision()
        elif self.kind is SourceReviewKind.AUTHENTICITY:
            if (
                self.authenticity is None
                or self.reliability is not None
                or self.expertise_basis is not None
                or self.credibility is not None
                or self.authenticity.evidence_id != self.target.capture_id
                or self.authenticity.issuer_id != self.target.source_id
            ):
                raise ValueError("Issuer authenticity cannot supply either assessment grade.")
        else:
            raise ValueError("Unsupported source review kind.")

    @property
    def key(self) -> str:
        return source_review_key(self.scope, self.kind, self.target)

    def source_revision(self) -> SourceRatingRevision:
        if self.reliability is None:
            raise ValueError("This revision does not grade source reliability.")
        return SourceRatingRevision(
            self.target.source_id,
            self.target.subject,
            self.reliability,
            self.expertise_basis,
            self.review,
        )

    def assertion_revision(self) -> AssertionRatingRevision:
        if self.credibility is None:
            raise ValueError("This revision does not grade assertion credibility.")
        return AssertionRatingRevision(
            self.target.capture_id, self.target.claim_id, self.credibility, self.review
        )


def validate_source_review_history(history: tuple[SourceReviewRevision, ...]) -> None:
    if type(history) is not tuple or len(history) > MAX_SOURCE_REVIEW_HISTORY:
        raise ValueError("Invalid bounded source review history.")
    previous = None
    for revision in history:
        if not isinstance(revision, SourceReviewRevision):
            raise ValueError("Invalid source review revision.")
        if previous is None:
            if revision.number != 1 or revision.review.supersedes is not None:
                raise ValueError("A review history must begin at its first revision.")
        elif (
            revision.key != previous.key
            or revision.scope != previous.scope
            or revision.number != previous.number + 1
            or revision.review.supersedes != previous.review.id
            or revision.review.recorded_at < previous.review.recorded_at
            or (
                revision.review.policy_version != previous.review.policy_version
                and revision.review.policy_note is None
            )
        ):
            raise ValueError("Source corrections require a consecutive, scoped review history.")
        previous = revision
