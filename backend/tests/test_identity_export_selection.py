"""Selected identity history is scoped and revalidated before package delivery."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import update

from ase.adapters.persistence.identity_models import IdentityRevisionRow
from ase.adapters.persistence.identity_payloads import encode_identity_revision
from ase.adapters.persistence.models import ReportRow, UserRow
from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    IdentityExportReference,
)
from ase.domain.errors import Conflict, InvalidRequest, NotFound, Unauthenticated
from ase.domain.identity_review import IdentityDisposition
from team_helpers import CONTEXT
from test_claim_repository import seed as seed_claim
from test_report_identity_service import VALUE, create, seed_report
from test_saved_map_views import claims_for


async def prepared(client, container, user):
    actor = await claims_for(client, container, user)
    report, version = await seed_report(container, user)
    revision = await create(container, actor, report)
    return actor, report, version, revision


async def test_exact_historical_identity_remains_selected_after_newer_correction(
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
            identity_references=(IdentityExportReference(first.decision_id, first.id),),
        )
        assert selected.identity_revisions == (first,) and selected.revisions == ()
        assert selected.report_version_id == version.id and not session.in_transaction()
        second = await container.report_identities(session).update(
            actor,
            first.decision_id,
            first.id,
            replace(VALUE, disposition=IdentityDisposition.REJECTED),
            CONTEXT,
        )
        await selector.recheck(actor, selected)
        assert selected.identity_revisions[0].id != second.id


@pytest.mark.parametrize(
    "change,error", [("owner", NotFound), ("account", Unauthenticated), ("revision", Conflict)]
)
async def test_scope_or_selected_identity_change_blocks_delivery(
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
            identity_references=(IdentityExportReference(first.decision_id, first.id),),
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
                payload, digest, size = encode_identity_revision(
                    replace(first, rationale="Altered retained content")
                )
                await mutating.execute(
                    update(IdentityRevisionRow)
                    .where(IdentityRevisionRow.id == first.id)
                    .values(payload=payload, content_sha256=digest, byte_size=size)
                )
            await mutating.commit()
        with pytest.raises(error):
            await selector.recheck(actor, selected)


async def test_mixed_parent_and_duplicate_identity_selections_are_rejected(client, container, user):
    actor, report, _, first = await prepared(client, container, user)
    _, _, claim = await seed_claim(container, user)
    ref = IdentityExportReference(first.decision_id, first.id)
    async with container.session_factory() as session:
        selector = container.export_claim_package(session).selector
        with pytest.raises(InvalidRequest, match="unique"):
            await selector.resolve(actor, report.id, 1, (), identity_references=(ref, ref))
        with pytest.raises(InvalidRequest, match="chosen report"):
            await selector.resolve(
                actor,
                report.id,
                1,
                (ClaimExportReference(claim.claim_id, claim.id),),
                identity_references=(ref,),
            )
        with pytest.raises(InvalidRequest, match="twenty"):
            await selector.resolve(actor, report.id, 1, (), identity_references=(ref,) * 21)
