"""Claim exports require exact authorised revisions and fresh access before delivery."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import update

from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.claims import SqlClaimRepository
from ase.adapters.persistence.models import ReportRow, UserRow
from ase.application.reports.claim_export_selection import ClaimExportReference, SelectClaimExport
from ase.domain.claim_revisions import ClaimReviewState
from ase.domain.errors import Conflict, InvalidRequest, NotFound, Unauthenticated
from team_helpers import CONTEXT, team_service
from test_claim_repository import seed
from test_report_team_scope import team_for
from test_saved_map_views import claims_for


async def test_exact_selection_rechecks_session_and_preserves_revision(client, container, user):
    actor = await claims_for(client, container, user)
    report, version, revision = await seed(container, user)
    async with container.session_factory() as session:
        selector = SelectClaimExport(
            container.report_claims(session),
            container.repositories(session).reports,
            container.repositories(session).uow,
        )
        selected = await selector.resolve(
            actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
        )
        assert selected.report_version_id == version.id and selected.revisions == (revision,)
        assert not session.in_transaction()
        await selector.recheck(actor, selected)
        with pytest.raises(Unauthenticated):
            await selector.recheck(
                replace(actor, security_version=actor.security_version + 1), selected
            )


async def test_foreign_personal_claim_cannot_be_selected(client, container, user):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, replace(user, id=uuid4()))
    async with container.session_factory() as session:
        selector = SelectClaimExport(
            container.report_claims(session),
            container.repositories(session).reports,
            container.repositories(session).uow,
        )
        with pytest.raises(NotFound):
            await selector.resolve(
                actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
            )


async def test_no_implicit_latest_or_mixed_report_selection(client, container, user):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, user)
    async with container.session_factory() as session:
        selector = SelectClaimExport(
            container.report_claims(session),
            container.repositories(session).reports,
            container.repositories(session).uow,
        )
        for references in ((), (ClaimExportReference(revision.claim_id, revision.id),) * 2):
            with pytest.raises(InvalidRequest):
                await selector.resolve(actor, report.id, 1, references)
        with pytest.raises(InvalidRequest):
            await selector.resolve(
                actor, uuid4(), 1, (ClaimExportReference(revision.claim_id, revision.id),)
            )


async def test_account_deactivated_after_selection_cannot_receive_export(client, container, user):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, user)
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        selector = SelectClaimExport(
            container.report_claims(session), repositories.reports, repositories.uow
        )
        selected = await selector.resolve(
            actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
        )
        async with container.session_factory() as other:
            await other.execute(
                update(UserRow).where(UserRow.id == user.id).values(is_active=False)
            )
            await other.commit()
        with pytest.raises(Unauthenticated):
            await selector.recheck(actor, selected)


async def test_new_correction_does_not_replace_explicit_historical_selection(
    client, container, user
):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, user)
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        selector = SelectClaimExport(
            container.report_claims(session), repositories.reports, repositories.uow
        )
        selected = await selector.resolve(
            actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
        )
        correction = replace(
            revision,
            id=uuid4(),
            number=2,
            previous_id=revision.id,
            state=ClaimReviewState.REVIEWED,
            reason="Checked original attribution.",
        )
        async with container.session_factory() as other:
            assert await SqlClaimRepository(other).append(correction, revision.id)
            await other.commit()
        await selector.recheck(actor, selected)
        assert selected.revisions == (revision,)


async def test_removed_team_member_cannot_receive_selected_export(client, container, user, admin):
    actor = await claims_for(client, container, user)
    team = await team_for(container, admin, user)
    report, _, revision = await seed(container, user)
    async with container.session_factory() as setup:
        await setup.execute(
            update(ReportRow).where(ReportRow.id == report.id).values(team_id=team.id)
        )
        await setup.execute(
            update(ClaimRow).where(ClaimRow.id == revision.claim_id).values(team_id=team.id)
        )
        await setup.commit()
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        selector = SelectClaimExport(
            container.report_claims(session), repositories.reports, repositories.uow
        )
        selected = await selector.resolve(
            actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
        )
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)
        with pytest.raises(NotFound):
            await selector.recheck(actor, selected)


@pytest.mark.parametrize("field", ["markdown", "title", "scope", "model"])
async def test_mutated_render_input_is_rejected(client, container, user, field):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, user)
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        selector = SelectClaimExport(
            container.report_claims(session), repositories.reports, repositories.uow
        )
        selected = await selector.resolve(
            actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
        )
        target = selected.record if field in {"title", "scope"} else selected.version
        setattr(target, field, {"question": "Replaced"} if field == "scope" else "Replaced")
        with pytest.raises(Conflict):
            await selector.recheck(actor, selected)
