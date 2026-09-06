"""Saved-map service retention, exact evidence anchors and current authority."""

from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from ase.adapters.persistence.map_view_models import MapViewRevisionRow, MapViewRow
from ase.adapters.persistence.operational_models import ReportVersionRow
from ase.application.research import map_views
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.map_view_records import revision_bytes
from ase.domain.map_views import MapCamera, MapViewState
from helpers import ADMIN_PASSWORD, USER_PASSWORD, login_token
from team_helpers import CONTEXT, team_service
from test_report_team_scope import save_team_report, team_for

STATE = MapViewState(MapCamera(179, 60, 4), selected_evidence="E1")
TITLE = "Frozen evidence"


async def claims_for(client, container, user):
    password = ADMIN_PASSWORD if user.is_admin else USER_PASSWORD
    return container.issuer.verify(await login_token(client, user.email, password))


async def create(container, claims, report_id, state=STATE):
    async with container.session_factory() as session:
        return await container.saved_map_views(session).create(
            claims, report_id, 1, TITLE, state, CONTEXT
        )


async def revise(container, claims, view, revision, *, version=1):
    async with container.session_factory() as session:
        return await container.saved_map_views(session).update(
            claims, view.id, revision.id, version, TITLE, STATE, CONTEXT
        )


async def invoke(service, operation, claims, report, view, revision):
    if operation == "create":
        return await service.create(claims, report.id, 1, TITLE, STATE, CONTEXT)
    if operation == "update":
        return await service.update(claims, view.id, revision.id, 1, TITLE, STATE, CONTEXT)
    if operation == "archive":
        return await service.archive(claims, view.id, CONTEXT)
    if operation == "get":
        return await service.get(claims, view.id, revision.id)
    return await service.list(claims, report.id)


@pytest.mark.parametrize("quota", ["views", "bytes"])
async def test_archived_views_keep_scope_quota_at_exact_threshold(
    client, container, user, monkeypatch, quota
):
    claims = await claims_for(client, container, user)
    report = await save_team_report(container, user, None)
    if quota == "views":
        monkeypatch.setattr(map_views, "MAX_SCOPE_VIEWS", 1)
    else:
        monkeypatch.setattr(map_views, "MAX_SCOPE_REVISION_BYTES", revision_bytes(STATE, TITLE))
    view, revision = await create(container, claims, report.id)
    async with container.session_factory() as session:
        service = container.saved_map_views(session)
        await service.archive(claims, view.id, CONTEXT)
        assert (await service.list(claims, report.id)).total == 0
        assert (await service.get(claims, view.id))[1] == revision
    other_report = await save_team_report(container, user, None)
    with pytest.raises(InvalidRequest, match="limit"):
        await create(container, claims, other_report.id)
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(MapViewRevisionRow)) == 1


@pytest.mark.parametrize("quota", ["revisions", "bytes"])
async def test_revision_limit_accepts_threshold_and_rejects_without_pointer_change(
    client, container, user, monkeypatch, quota
):
    claims = await claims_for(client, container, user)
    report = await save_team_report(container, user, None)
    if quota == "revisions":
        monkeypatch.setattr(map_views, "MAX_VIEW_REVISIONS", 2)
    else:
        monkeypatch.setattr(map_views, "MAX_SCOPE_REVISION_BYTES", 2 * revision_bytes(STATE, TITLE))
    view, original = await create(container, claims, report.id)
    view, latest = await revise(container, claims, view, original)
    with pytest.raises(InvalidRequest, match="limit"):
        await revise(container, claims, view, latest)
    async with container.session_factory() as session:
        service = container.saved_map_views(session)
        assert (await service.get(claims, view.id))[1] == latest
        assert (await service.get(claims, view.id, original.id))[1] == original
        assert await session.scalar(select(func.count()).select_from(MapViewRevisionRow)) == 2


async def test_admin_personal_creation_keeps_parent_owner_and_charges_that_scope(
    client, container, admin, user, monkeypatch
):
    owner_claims = await claims_for(client, container, user)
    admin_claims = await claims_for(client, container, admin)
    report = await save_team_report(container, user, None)
    monkeypatch.setattr(map_views, "MAX_SCOPE_VIEWS", 1)
    view, revision = await create(container, admin_claims, report.id)
    assert view.created_by == user.id and view.team_id is None
    assert revision.created_by == admin.id
    with pytest.raises(InvalidRequest, match="saved-map limit"):
        await create(container, owner_claims, report.id)
    async with container.session_factory() as session:
        service = container.saved_map_views(session)
        assert (await service.get(owner_claims, view.id))[1] == revision
        assert await service.views.scope_usage(admin.id, None) == (0, 0)
    await revise(container, owner_claims, view, revision)


async def test_team_quota_is_shared_between_creators(client, container, admin, user, monkeypatch):
    team = await team_for(container, admin, user)
    report = await save_team_report(container, user, team.id)
    owner_claims = await claims_for(client, container, user)
    admin_claims = await claims_for(client, container, admin)
    monkeypatch.setattr(map_views, "MAX_SCOPE_VIEWS", 1)
    await create(container, owner_claims, report.id)
    with pytest.raises(InvalidRequest, match="saved-map limit"):
        await create(container, admin_claims, report.id)
    personal = await save_team_report(container, user, None)
    await create(container, owner_claims, personal.id)


@pytest.mark.parametrize("change", ["revoked_family", "removed_member", "archived_team"])
async def test_current_authority_is_rechecked_for_every_operation(
    client, container, admin, user, change
):
    team = await team_for(container, admin, user)
    report = await save_team_report(container, user, team.id)
    claims = await claims_for(client, container, user)
    view, revision = await create(container, claims, report.id)
    if change == "revoked_family":
        async with container.session_factory() as session:
            await container.repositories(session).refresh_tokens.revoke_family(
                claims.family_id, container.clock.now()
            )
            await session.commit()
        error = Unauthenticated
    else:
        async with team_service(container) as service:
            if change == "removed_member":
                await service.remove_member(admin, team.id, user.id, CONTEXT)
            else:
                await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
        error = NotFound if change == "removed_member" else Forbidden
    for operation in ("create", "update", "archive", "get", "list"):
        async with container.session_factory() as session:
            service = container.saved_map_views(session)
            if change == "archived_team" and operation in {"get", "list"}:
                if operation == "get":
                    assert (await service.get(claims, view.id, revision.id))[1] == revision
                else:
                    assert (await service.list(claims, report.id)).total == 1
                continue
            with pytest.raises(error):
                await invoke(service, operation, claims, report, view, revision)
    if change == "archived_team":
        admin_claims = await claims_for(client, container, admin)
        await revise(container, admin_claims, view, revision)


async def test_exact_frozen_version_survives_new_versions_and_archive_url_changes(
    client, container, user
):
    claims = await claims_for(client, container, user)
    report = await save_team_report(container, user, None)
    view, revision = await create(container, claims, report.id)
    async with container.session_factory() as session:
        reports = container.repositories(session).reports
        original = await reports.get_version(report.id, 1)
        assert revision.report_version_id == original.id
        assert revision.evidence_sha256 == evidence_digest(original)
        changed = replace(original.evidence[0], summary="Different frozen evidence")
        report.latest_version = 2
        await reports.add_version(
            report, replace(original, id=uuid4(), number=2, evidence=(changed,))
        )
        row = await session.get(ReportVersionRow, original.id)
        row.evidence = [{**item, "archive_url": None} for item in row.evidence]
        await session.commit()
    async with container.session_factory() as session:
        assert (await container.saved_map_views(session).get(claims, view.id))[1] == revision
    latest_view, latest = await revise(container, claims, view, revision, version=2)
    assert latest.evidence_sha256 != revision.evidence_sha256
    async with container.session_factory() as session:
        assert (await container.saved_map_views(session).get(claims, latest_view.id, revision.id))[
            1
        ] == revision


@pytest.mark.parametrize(
    "state",
    [replace(STATE, selected_evidence="E999"), replace(STATE, source_ids=("foreign-source",))],
)
async def test_selection_must_belong_to_exact_frozen_version(client, container, user, state):
    claims = await claims_for(client, container, user)
    report = await save_team_report(container, user, None)
    with pytest.raises(InvalidRequest, match="report version"):
        await create(container, claims, report.id, state)
    async with container.session_factory() as session:
        assert (await container.saved_map_views(session).list(claims, report.id)).total == 0
        assert await session.scalar(select(func.count()).select_from(MapViewRevisionRow)) == 0


@pytest.mark.parametrize("tamper", ["evidence", "title", "version_id", "scope"])
async def test_changed_integrity_anchors_are_not_silently_reproduced(
    client, container, user, admin, tamper
):
    claims = await claims_for(client, container, user)
    report = await save_team_report(container, user, None)
    view, revision = await create(container, claims, report.id)
    async with container.session_factory() as session:
        if tamper == "evidence":
            row = await session.get(ReportVersionRow, revision.report_version_id)
            row.evidence = [{**item, "summary": "Changed"} for item in row.evidence]
        elif tamper == "scope":
            await session.execute(
                update(MapViewRow).where(MapViewRow.id == view.id).values(created_by=admin.id)
            )
        else:
            values = {"title": "Changed"}
            if tamper == "version_id":
                foreign = await save_team_report(container, user, None)
                other = await container.repositories(session).reports.get_version(foreign.id, 1)
                values = {"report_version_id": other.id}
            await session.execute(
                update(MapViewRevisionRow)
                .where(MapViewRevisionRow.id == revision.id)
                .values(**values)
            )
        await session.commit()
    actor = await claims_for(client, container, admin) if tamper == "scope" else claims
    error = (
        InvalidRequest if tamper == "scope" else NotFound if tamper == "version_id" else Conflict
    )
    async with container.session_factory() as session:
        with pytest.raises(error):
            await container.saved_map_views(session).get(actor, view.id)


async def test_stale_base_and_failed_conditional_append_leave_no_revision(
    client, container, user, monkeypatch
):
    claims = await claims_for(client, container, user)
    report = await save_team_report(container, user, None)
    view, original = await create(container, claims, report.id)
    view, latest = await revise(container, claims, view, original)
    with pytest.raises(Conflict):
        await revise(container, claims, view, original)
    async with container.session_factory() as session:
        service = container.saved_map_views(session)
        real_append = service.views.append

        async def append_then_conflict(candidate, base):
            assert await real_append(candidate, base)
            return False

        monkeypatch.setattr(service.views, "append", append_then_conflict)
        rollback = AsyncMock(wraps=service.uow.rollback)
        monkeypatch.setattr(service.uow, "rollback", rollback)
        with pytest.raises(Conflict):
            await service.update(claims, view.id, latest.id, 1, TITLE, STATE, CONTEXT)
        rollback.assert_awaited_once()
    async with container.session_factory() as session:
        assert (await container.saved_map_views(session).get(claims, view.id))[1] == latest
        assert await session.scalar(select(func.count()).select_from(MapViewRevisionRow)) == 2
