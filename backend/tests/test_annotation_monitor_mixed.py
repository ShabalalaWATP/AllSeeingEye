"""Real persistence and release checks preserve all three independently reviewed kinds."""

from dataclasses import replace

import pytest

from annotation_monitor_helpers import correct
from ase.adapters.persistence.claims import SqlClaimRepository
from ase.adapters.persistence.identity_decisions import SqlIdentityDecisionRepository
from ase.adapters.persistence.relationship_reviews import SqlRelationshipReviewRepository
from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    IdentityExportReference,
    RelationshipExportReference,
)
from ase.application.reports.comparison_inputs import ComparisonSelection
from ase.application.reports.identities import IdentityReviewInput
from ase.application.reports.relationships import RelationshipReviewInput
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.claim_revisions import ClaimCitationInput, ClaimRelation, revise_claim
from ase.domain.identity_review import revise_identity_decision
from ase.domain.relationship_review import revise_relationship_review
from ase.domain.research_context import build_research_context
from report_documents_helpers import document_records
from team_helpers import CONTEXT
from test_annotation_monitoring import tick
from test_claim_revisions import revision_args
from test_identity_review import arguments as identity_arguments
from test_relationship_review import arguments as relationship_arguments
from test_saved_map_views import claims_for


@pytest.mark.parametrize("inventory", [False, True])
async def test_all_three_actual_revision_mutations_are_queued_and_observed_independently(
    client, container, user, inventory
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
        **{
            **revision_args(),
            "version": version,
            "now": container.clock.now(),
            "actor_id": user.id,
            "citations": (citation,),
        }
    )
    identity = revise_identity_decision(
        **{
            **identity_args,
            "version": version,
            "candidate_label": "I1",
            "now": container.clock.now(),
            "actor_id": user.id,
        }
    )
    relationship = revise_relationship_review(
        **{
            **relationship_args,
            "version": version,
            "evidence_label": "R1",
            "now": container.clock.now(),
            "actor_id": user.id,
        }
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
        if inventory:
            await session.commit()
            monitor = await container.annotation_monitors(session).create(
                actor,
                "New roots",
                ComparisonSelection(report.id, 1),
                ("claim", "identity", "relationship"),
                True,
                "report_inventory",
            )
        digest = evidence_digest(version)
        await SqlClaimRepository(session).create(claim, digest)
        await SqlIdentityDecisionRepository(session).create(identity, digest)
        await SqlRelationshipReviewRepository(session).create(relationship, digest)
        await session.commit()
        if not inventory:
            monitor = await container.annotation_monitors(session).create(
                actor, "Mixed watch", selection, ("claim", "identity", "relationship"), True
            )
    await correct(container, actor, claim)
    async with container.session_factory() as session:
        await container.report_identities(session).update(
            actor,
            identity.decision_id,
            identity.id,
            IdentityReviewInput("I1", identity.disposition, "Corrected identity explanation."),
            CONTEXT,
        )
        await container.report_relationships(session).update(
            actor,
            relationship.relationship_id,
            relationship.id,
            RelationshipReviewInput(
                "R1", relationship.disposition, "Corrected relationship explanation."
            ),
            CONTEXT,
        )
    for _ in range(6 if inventory else 3):
        assert await tick(container, monitor.id)
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        rows, total = await container.annotation_monitors(session).repository.history(
            monitor.id, 20, 0
        )
        assert total == (6 if inventory else 3) and {row.changed_categories for row in rows} == {
            ("claim",),
            ("identity",),
            ("relationship",),
        }
        assert all(row.alert_id is not None for row in rows)
