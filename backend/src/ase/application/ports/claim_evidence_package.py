"""Offline selected-revision package renderer boundary."""

from typing import Protocol

from ase.domain.claim_revisions import ClaimRevision
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.original_assets import OriginalAssetContent
from ase.domain.relationship_review import RelationshipReviewRevision
from ase.domain.report_records import ReportRecord, ReportVersion


class ClaimEvidencePackageRenderer(Protocol):
    def render(
        self,
        record: ReportRecord,
        version: ReportVersion,
        revisions: tuple[ClaimRevision, ...],
        *,
        identity_revisions: tuple[IdentityDecisionRevision, ...] = (),
        relationship_revisions: tuple[RelationshipReviewRevision, ...] = (),
        original_assets: tuple[OriginalAssetContent, ...] = (),
    ) -> bytes: ...
