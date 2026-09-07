"""Projection, predecessor and current-session checks protect independent relationship reviews."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.models import AuditLogRow, RefreshTokenRow
from ase.adapters.persistence.relationship_models import RelationshipRevisionRow
from ase.adapters.persistence.relationship_payloads import encode_relationship_revision
from ase.domain.errors import Conflict, Unauthenticated
from helpers import USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT
from test_report_relationship_service import VALUE, create, seed_report
from test_saved_map_views import claims_for


async def test_projection_exposes_source_dates_and_existing_review_mapping(client, container, user):
    record, version = await seed_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    path = "/api/relationship-reviews/assertions"
    params = {"report_id": str(record.id), "version_number": 1}
    response = await client.get(path, params=params, headers=headers)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    snapshot = response.json()["items"][0]
    assert snapshot["evidence_label"] == "E1"
    assert snapshot["captured_at"] == version.evidence[0].captured_at.isoformat().replace(
        "+00:00", "Z"
    )
    assert response.json()["review_ids"] == {}
    actor = await claims_for(client, container, user)
    first = await create(container, actor, record)
    response = await client.get(path, params=params, headers=headers)
    assert response.json()["review_ids"] == {"E1": str(first.relationship_id)}
    assert response.json()["items"][0] == snapshot


@pytest.mark.parametrize("change", ["revoked", "mfa"])
async def test_projection_and_mutation_require_live_mfa_session(client, container, admin, change):
    actor = await claims_for(client, container, admin)
    record, _ = await seed_report(container, admin)
    first = await create(container, actor, record)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        if change == "revoked":
            await repos.refresh_tokens.revoke_family(actor.family_id, container.clock.now())
        else:
            await session.execute(
                update(RefreshTokenRow)
                .where(RefreshTokenRow.family_id == actor.family_id)
                .values(mfa_verified=False)
            )
        await session.commit()
        service = container.report_relationships(session)
        with pytest.raises(Unauthenticated):
            await service.assertions(actor, record.id, 1)
        with pytest.raises(Unauthenticated):
            await service.update(actor, first.relationship_id, first.id, VALUE, CONTEXT)


async def test_corrupt_predecessor_cannot_hide_behind_a_valid_latest_revision(
    client, container, user
):
    actor = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    first = await create(container, actor, record)
    async with container.session_factory() as session:
        service = container.report_relationships(session)
        second = await service.update(actor, first.relationship_id, first.id, VALUE, CONTEXT)
        invalid = replace(first, report_version_id=uuid4())
        payload, digest, size = encode_relationship_revision(invalid)
        await session.execute(
            update(RelationshipRevisionRow)
            .where(RelationshipRevisionRow.id == first.id)
            .values(payload=payload, content_sha256=digest, byte_size=size)
        )
        await session.commit()
        with pytest.raises(Conflict):
            await service.get(actor, second.relationship_id)
        with pytest.raises(Conflict):
            await service.assertions(actor, record.id, 1)


async def test_audit_retains_identifiers_without_rationale_or_source_text(client, container, user):
    actor = await claims_for(client, container, user)
    record, _ = await seed_report(container, user)
    first = await create(container, actor, record)
    async with container.session_factory() as session:
        rows = (
            await session.scalars(
                select(AuditLogRow).where(AuditLogRow.action == "relationship.created")
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].details == {
            "report_id": str(record.id),
            "revision_id": str(first.id),
            "number": 1,
        }
        assert rows[0].subject == str(first.relationship_id)
