"""Explicit revision selections, independent of mutable latest-review pointers."""

from dataclasses import dataclass
from uuid import UUID

from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    IdentityExportReference,
    RelationshipExportReference,
)
from ase.domain.annotation_comparison import AnnotationCorrespondence, JudgementCorrespondence


@dataclass(frozen=True, slots=True)
class ComparisonSelection:
    report_id: UUID
    version_number: int
    revisions: tuple[ClaimExportReference, ...] = ()
    identity_revisions: tuple[IdentityExportReference, ...] = ()
    relationship_revisions: tuple[RelationshipExportReference, ...] = ()


@dataclass(frozen=True, slots=True)
class ComparisonInput:
    before: ComparisonSelection
    after: ComparisonSelection
    correspondences: tuple[AnnotationCorrespondence, ...] = ()
    judgement_correspondences: tuple[JudgementCorrespondence, ...] = ()
