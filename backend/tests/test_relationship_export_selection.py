"""Selected relationship history is scoped and revalidated before package delivery."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import update

from ase.adapters.persistence.models import ReportRow, UserRow
from ase.adapters.persistence.relationship_models import RelationshipRevisionRow
from ase.adapters.persistence.relationship_payloads import encode_relationship_revision
from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    RelationshipExportReference,
)
from ase.domain.errors import Conflict, InvalidRequest, NotFound, Unauthenticated
from ase.domain.relationship_review import RelationshipDisposition
from team_helpers import CONTEXT
from test_claim_repository import seed as seed_claim
from test_report_relationship_service import VALUE, create, seed_report
from test_saved_map_views import claims_for


async def prepared(client, container, user):
    actor = await claims_for(client, container, user)
    report, version = await seed_report(container, user)
    revision = await create(container, actor, report)
    return actor, report, version, revision


async def test_exact_historical_relationship_remains_selected_after_newer_correction(
    client, container, user
):
    actor, report, version, first = await prepared(client, container, user)
    async with container.session_factory() as session:
        selector = container.export_claim_package(session).selector
        selected = await selector.resolve(
            actor,
            report.id,
            1,
            (),
            relationship_references=(RelationshipExportReference(first.relationship_id, first.id),),
        )
        assert selected.relationship_revisions == (first,) and selected.revisions == ()
        assert selected.report_version_id == version.id and not session.in_transaction()
        second = await container.report_relationships(session).update(
            actor,
            first.relationship_id,
            first.id,
            replace(VALUE, disposition=RelationshipDisposition.DISPUTED),
            CONTEXT,
        )
        await selector.recheck(actor, selected)
        assert selected.relationship_revisions[0].id != second.id


@pytest.mark.parametrize(
    "change,error", [("owner", NotFound), ("account", Unauthenticated), ("revision", Conflict)]
)
async def test_scope_or_selected_relationship_change_blocks_delivery(
    client, container, user, change, error
):
    actor, report, _, first = await prepared(client, container, user)
    async with container.session_factory() as session:
        selector = container.export_claim_package(session).selector
        selected = await selector.resolve(
            actor,
            report.id,
            1,
            (),
            relationship_references=(RelationshipExportReference(first.relationship_id, first.id),),
        )
        async with container.session_factory() as mutating:
            if change == "owner":
                await mutating.execute(
                    update(ReportRow).where(ReportRow.id == report.id).values(created_by=uuid4())
                )
            elif change == "account":
                await mutating.execute(
                    update(UserRow).where(UserRow.id == user.id).values(is_active=False)
                )
            else:
                payload, digest, size = encode_relationship_revision(
                    replace(first, rationale="Altered retained content")
                )
                await mutating.execute(
                    update(RelationshipRevisionRow)
                    .where(RelationshipRevisionRow.id == first.id)
                    .values(payload=payload, content_sha256=digest, byte_size=size)
                )
            await mutating.commit()
        with pytest.raises(error):
            await selector.recheck(actor, selected)


async def test_mixed_parent_and_duplicate_relationship_selections_are_rejected(
    client, container, user
):
    actor, report, _, first = await prepared(client, container, user)
    _, _, claim = await seed_claim(container, user)
    ref = RelationshipExportReference(first.relationship_id, first.id)
    async with container.session_factory() as session:
        selector = container.export_claim_package(session).selector
        with pytest.raises(InvalidRequest, match="selected once"):
            await selector.resolve(actor, report.id, 1, (), relationship_references=(ref, ref))
        with pytest.raises(InvalidRequest, match="chosen report"):
            await selector.resolve(
                actor,
                report.id,
                1,
                (ClaimExportReference(claim.claim_id, claim.id),),
                relationship_references=(ref,),
            )
        with pytest.raises(InvalidRequest, match="twenty"):
            await selector.resolve(actor, report.id, 1, (), relationship_references=(ref,) * 21)
