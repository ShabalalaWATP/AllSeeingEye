"""Claim persistence retains exact scope, immutable history and conditional updates."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.claim_models import ClaimRevisionRow, ClaimRow
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


async def seed(container, user):
    report, version = document_records(user.id)
    item = version.evidence[0]
    revision = revise_claim(
        version=version,
        revision_id=uuid4(),
        claim_id=uuid4(),
        previous=None,
        statement="The captured source reports this observation.",
        kind=ClaimKind.REPORTED_FACT,
        state=ClaimReviewState.PROPOSED,
        citations=(
            ClaimCitationInput(
                item.label, ClaimRelation.SUPPORTING, "title", 0, len(item.title), item.title
            ),
        ),
        unresolved_conflicts=(),
        reason="Record assertion for review.",
        actor_id=uuid4(),
        now=container.clock.now(),
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(report, version)
        await SqlClaimRepository(session).create(revision, evidence_digest(version))
        await session.commit()
    return report, version, revision


async def test_roundtrip_stale_correction_and_parent_scope(container, user):
    report, _, first = await seed(container, user)
    second = replace(
        first,
        id=uuid4(),
        number=2,
        previous_id=first.id,
        state=ClaimReviewState.REVIEWED,
        reason="Reviewed excerpt attribution.",
    )
    async with container.session_factory() as session:
        repo = SqlClaimRepository(session)
        assert await repo.revision(first.claim_id, first.id) == first
        assert await repo.revision(uuid4(), first.id) is None
        root = await session.get(ClaimRow, first.claim_id)
        assert root.created_by == report.created_by != first.authored_by
        assert root.report_version_id == first.report_version_id
        assert await repo.append(second, first.id)
        await session.commit()
    async with container.session_factory() as session:
        repo = SqlClaimRepository(session)
        assert not await repo.append(replace(second, id=uuid4()), first.id)
        assert await repo.revision(first.claim_id, first.id) == first
        assert await repo.revision(first.claim_id, second.id) == second
        assert (await session.get(ClaimRow, first.claim_id)).latest_revision_id == second.id


@pytest.mark.parametrize("change", ["report", "version", "number", "time"])
async def test_append_rejects_anchor_or_sequence_changes(container, user, change):
    _, _, first = await seed(container, user)

    second = replace(first, id=uuid4(), number=2, previous_id=first.id)
    if change == "report":
        second = replace(second, report_id=uuid4())
    elif change == "version":
        second = replace(second, report_version_id=uuid4())
    elif change == "number":
        second = replace(second, number=4)
    else:
        second = replace(second, created_at=first.created_at - timedelta(seconds=1))
    async with container.session_factory() as session:
        assert not await SqlClaimRepository(session).append(second, first.id)
        assert await session.get(ClaimRevisionRow, second.id) is None


async def test_payload_corruption_is_detected(container, user):
    _, _, first = await seed(container, user)
    async with container.session_factory() as session:
        row = await session.get(ClaimRevisionRow, first.id)
        payload = {**row.payload, "statement": "Changed without a revision."}
        await session.execute(
            update(ClaimRevisionRow).where(ClaimRevisionRow.id == first.id).values(payload=payload)
        )
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(ValueError, match="integrity"):
            await SqlClaimRepository(session).revision(first.claim_id, first.id)


async def test_explicit_deletion_removes_all_history(container, user):
    report, _, first = await seed(container, user)
    async with container.session_factory() as session:
        repo = SqlClaimRepository(session)
        assert await repo.append(
            replace(first, id=uuid4(), number=2, previous_id=first.id), first.id
        )
        await container.repositories(session).reports.delete(report.id)
        await session.commit()
        assert list(await session.scalars(select(ClaimRevisionRow))) == []
        assert await session.get(ClaimRow, first.claim_id) is None
