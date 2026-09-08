"""Initial annotation fixtures for schemas predating transactional monitor fanout.

Historical migration tests deliberately stay on their old schema. These writers
retain that schema's roots/payloads rather than invoking a current application
repository which also writes new monitoring tables.
"""

from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.claims import _row as claim_row
from ase.adapters.persistence.identity_decisions import _row as identity_row
from ase.adapters.persistence.identity_models import IdentityDecisionRow
from ase.adapters.persistence.operational_models import ReportRow, ReportVersionRow
from ase.adapters.persistence.relationship_models import RelationshipReviewRow
from ase.adapters.persistence.relationship_reviews import _row as relationship_row
from ase.domain.claim_revisions import ClaimRevision
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.relationship_review import RelationshipReviewRevision


async def seed_initial(session, revision, evidence_sha256):
    assert revision.number == 1 and revision.previous_id is None
    parent = await session.get(ReportRow, revision.report_id)
    version = await session.get(ReportVersionRow, revision.report_version_id)
    assert parent is not None and version is not None and version.report_id == parent.id
    common = {
        "report_id": revision.report_id,
        "report_version_id": revision.report_version_id,
        "created_by": revision.authored_by if parent.team_id is not None else parent.created_by,
        "team_id": parent.team_id,
        "evidence_sha256": evidence_sha256,
        "latest_revision_id": revision.id,
        "created_at": revision.created_at,
    }
    if isinstance(revision, ClaimRevision):
        root = ClaimRow(id=revision.claim_id, **common)
        payload = claim_row(revision)
    elif isinstance(revision, IdentityDecisionRevision):
        root = IdentityDecisionRow(
            id=revision.decision_id,
            subject=revision.subject,
            candidate_label=revision.candidate.candidate.evidence_label,
            **common,
        )
        payload = identity_row(revision)
    elif isinstance(revision, RelationshipReviewRevision):
        root = RelationshipReviewRow(
            id=revision.relationship_id, evidence_label=revision.assertion.evidence_label, **common
        )
        payload = relationship_row(revision)
    else:
        raise AssertionError("Choose an exact supported initial annotation revision")
    session.add(root)
    await session.flush()
    session.add(payload)
    await session.flush()
