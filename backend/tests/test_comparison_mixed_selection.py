"""Real persistence and release checks preserve all three independently reviewed kinds."""

import json
from dataclasses import replace

from ase.adapters.persistence.claims import SqlClaimRepository
from ase.adapters.persistence.identity_decisions import SqlIdentityDecisionRepository
from ase.adapters.persistence.relationship_reviews import SqlRelationshipReviewRepository
from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    IdentityExportReference,
    RelationshipExportReference,
)
from ase.application.reports.comparison_inputs import ComparisonInput, ComparisonSelection
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.claim_revisions import ClaimCitationInput, ClaimRelation, revise_claim
from ase.domain.identity_review import revise_identity_decision
from ase.domain.relationship_review import revise_relationship_review
from ase.domain.research_context import build_research_context
from report_documents_helpers import document_records
from test_claim_revisions import revision_args
from test_identity_review import arguments as identity_arguments
from test_relationship_review import arguments as relationship_arguments
from test_saved_map_views import claims_for


async def test_mixed_exact_selection_roundtrips_claim_identity_and_relationship(
    client, container, user
):
    actor = await claims_for(client, container, user)
    report, version = document_records(user.id)
    identity_args, relationship_args = identity_arguments(), relationship_arguments()
    report = replace(
        report, scope={"research_focus": "company", "research_subject": identity_args["subject"]}
    )
    identity_item = replace(
        identity_args["version"].evidence[0], label="I1", event_id="identity-record"
    )
    relationship_item = replace(
        relationship_args["version"].evidence[0], label="R1", event_id="relation-record"
    )
    version = replace(version, evidence=(*version.evidence, identity_item, relationship_item))
    version.research_context = build_research_context(version.evidence)
    item = version.evidence[0]
    citation = ClaimCitationInput(
        item.label, ClaimRelation.SUPPORTING, "title", 0, len(item.title), item.title
    )
    claim = revise_claim(
        **{**revision_args(), "version": version, "actor_id": user.id, "citations": (citation,)}
    )
    identity = revise_identity_decision(
        **{**identity_args, "version": version, "candidate_label": "I1", "actor_id": user.id}
    )
    relationship = revise_relationship_review(
        **{**relationship_args, "version": version, "evidence_label": "R1", "actor_id": user.id}
    )
    selection = ComparisonSelection(
        report.id,
        1,
        (ClaimExportReference(claim.claim_id, claim.id),),
        (IdentityExportReference(identity.decision_id, identity.id),),
        (RelationshipExportReference(relationship.relationship_id, relationship.id),),
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(report, version)
        digest = evidence_digest(version)
        await SqlClaimRepository(session).create(claim, digest)
        await SqlIdentityDecisionRepository(session).create(identity, digest)
        await SqlRelationshipReviewRepository(session).create(relationship, digest)
        await session.commit()
        service = container.annotation_comparisons(session)
        request = ComparisonInput(selection, selection)
        preview = await service.execute(actor, request)
        manifest = json.loads(
            (await service.execute(actor, request, preview.comparison_sha256)).content
        )
    assert {row.kind for row in preview.annotation_changes} == {"claim", "identity", "relationship"}
    assert all(row.status == "unchanged" for row in preview.annotation_changes)
    assert manifest["before"]["identity_revisions"][0]["id"] == str(identity.id)
    assert (
        manifest["after"]["relationship_revisions"][0]["assertion"]["parent_lei"]
        == relationship.assertion.parent_lei
    )
    assert manifest["compared_by"] == str(user.id)
