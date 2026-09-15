"""Synthetic review and origin records, without providers or mutable source stores."""

from datetime import UTC, datetime

from ase.domain.events import Credibility, Reliability
from ase.domain.origin_records import OriginEdge, OriginNode, OriginRelation, OriginRole
from ase.domain.source_assessment import (
    ASSESSMENT_POLICY_VERSION,
    AssertionRatingRevision,
    Assessor,
    RatingReview,
    RatingStatus,
    SourceRatingRevision,
)

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


def review(id_="r1", **changes):
    return RatingReview(
        **{
            "id": id_,
            "assessor": Assessor.POLICY,
            "assessor_id": "editorial-policy",
            "status": RatingStatus.APPLIED,
            "basis": "Observed corrections and documented methods.",
            "policy_version": ASSESSMENT_POLICY_VERSION,
            "recorded_at": NOW,
            **changes,
        }
    )


def source(grade=Reliability.A, **changes):
    return SourceRatingRevision(
        **{
            "source_id": "statistics-office",
            "subject": "population-statistics",
            "reliability": grade,
            "expertise_basis": "Published census methodology and audit.",
            "review": review(),
            **changes,
        }
    )


def assertion(grade=Credibility.CONFIRMED, **changes):
    return AssertionRatingRevision(
        **{
            "evidence_id": "E1",
            "claim_id": "C1",
            "credibility": grade,
            "review": review(
                "a1", basis="Exact table agrees with an independent recorded dataset."
            ),
            **changes,
        }
    )


def node(id_="N1", **changes):
    return OriginNode(
        **{
            "id": id_,
            "evidence_id": "E" + id_[1:],
            "claim_id": "C1",
            "source_id": "statistics-office" if id_ == "N1" else id_,
            "role": OriginRole.ORIGINAL_DOCUMENT,
            "organisation": "org-" + id_,
            "original_identity": "document-" + id_,
            **changes,
        }
    )


def edge(id_="link-1", child="N2", parent="N1", **changes):
    return OriginEdge(
        **{
            "id": id_,
            "child_id": child,
            "parent_id": parent,
            "relation": OriginRelation.TRANSLATION,
            "reason": "The passage credits the original.",
            "assessor": Assessor.MODEL,
            "assessor_id": "proposer",
            "method": "origin-proposal-v1",
            "recorded_at": NOW,
            **changes,
        }
    )
