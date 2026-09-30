"""Independent frozen observations for forecast lifecycle API tests."""

from dataclasses import replace
from uuid import uuid4

from ase.adapters.persistence.claims import SqlClaimRepository
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimKind,
    ClaimRelation,
    ClaimReviewState,
    revise_claim,
)
from report_documents_helpers import document_records


async def later_observation(container, user):
    now = container.clock.now()
    report, version = document_records(user.id)
    report = replace(report, created_at=now)
    evidence = replace(version.evidence[0], published_at=now, observed_at=now)
    version = replace(version, created_at=now, evidence=(evidence,))
    revision = revise_claim(
        version=version,
        revision_id=uuid4(),
        claim_id=uuid4(),
        previous=None,
        statement="Later evidence establishes the road's condition.",
        kind=ClaimKind.REPORTED_FACT,
        state=ClaimReviewState.PROPOSED,
        citations=(
            ClaimCitationInput(
                evidence.label,
                ClaimRelation.SUPPORTING,
                "title",
                0,
                len(evidence.title),
                evidence.title,
            ),
        ),
        unresolved_conflicts=(),
        reason="Reviewed later frozen observation.",
        actor_id=user.id,
        now=now,
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(report, version)
        await SqlClaimRepository(session).create(revision, evidence_digest(version))
        reviewed = replace(
            revision, id=uuid4(), number=2, previous_id=revision.id, state=ClaimReviewState.REVIEWED
        )
        assert await SqlClaimRepository(session).append(reviewed, revision.id)
        await session.commit()
    revision = reviewed
    citation = revision.citations[0]
    return {
        "report_id": str(report.id),
        "version": 1,
        "claim_id": str(revision.claim_id),
        "claim_revision_id": str(revision.id),
        "citation": {"evidence_label": citation.label, "excerpt_sha256": citation.excerpt.sha256},
    }
