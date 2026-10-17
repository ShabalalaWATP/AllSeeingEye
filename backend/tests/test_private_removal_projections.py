"""Account graphs keep independent copies and remove only settled private projections."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.original_asset_models import OriginalAssetRow
from ase.adapters.persistence.report_team_copy_models import ReportTeamCopyRow
from ase.adapters.persistence.selected_index_models import SelectedIndexRecordRow
from ase.domain.errors import Conflict, NotFound
from ase.domain.private_removal import RemovalRequest, RemovalScope
from dormant_retention_helpers import seed, selected_row
from private_removal_helpers import apply, authorise, preview, report, subscription
from team_helpers import CONTEXT, team_service


@pytest.mark.parametrize("external", [False, True])
async def test_selected_corrections_do_not_mutate_surviving_subscriptions(
    container, user, admin, external
):
    await authorise(container, admin, user)
    schedule, _ = await subscription(container, user)
    other, _ = await subscription(container, user) if external else (schedule, None)
    now = container.clock.now()
    # Exercise a full deletion chunk with internal self-references, with FK enforcement.
    async with container.session_factory() as session:
        if session.bind.dialect.name == "sqlite":
            await session.execute(text("PRAGMA foreign_keys=ON"))
        for number in range(1, 102):
            session.add(
                selected_row(
                    schedule.id,
                    user.id,
                    number,
                    now,
                    corrects_id=number - 1 if number > 1 else None,
                )
            )
            await session.flush()
        if external:
            session.add(selected_row(other.id, user.id, 102, now, corrects_id=1))
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.SUBSCRIPTION, schedule.id)
    plan = await preview(container, admin, request)
    if external:
        assert "retained_foreign_key_dependency" in plan.blockers
        with pytest.raises(Conflict, match="blocked"):
            await apply(container, admin, request, plan.fingerprint)
        async with container.session_factory() as session:
            assert (await session.get(SelectedIndexRecordRow, 102)).corrects_id == 1
    else:
        assert not plan.blockers
        assert plan.counts["selected_index_records"] == 101
        await apply(container, admin, request, plan.fingerprint)
        async with container.session_factory() as session:
            assert await session.scalar(select(SelectedIndexRecordRow)) is None


@pytest.mark.parametrize("state", ["uploading", "expired_upload", "active", "foreign_uploader"])
async def test_original_bytes_and_upload_reservations_are_inventoried(
    container, user, admin, state, monkeypatch
):
    await authorise(container, admin, user)
    target, version = await report(container, user)
    now = container.clock.now()
    content = b"x" * 4096 if state in {"active", "foreign_uploader"} else None
    asset = OriginalAssetRow(
        id=uuid4(),
        report_id=target.id,
        report_version_id=version.id,
        version_number=1,
        evidence_label="E1",
        source_id="test",
        event_id="test",
        sha256="a" * 64,
        byte_count=4096,
        filename="private.txt",
        media_type="text/plain",
        permitted_use="test",
        owner_id=user.id,
        team_id=None,
        uploader_id=admin.id if state == "foreign_uploader" else user.id,
        created_at=now,
        expires_at=now + timedelta(days=1),
        reservation_expires_at=now + timedelta(seconds=-1 if state == "expired_upload" else 60),
        status="active" if content else "uploading",
        content=content,
    )
    await seed(container, asset)
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    plan = await preview(container, admin, request)
    assert plan.counts["original_assets"] == 1
    if state == "uploading":
        assert "active_original_asset_upload" in plan.blockers
    elif state == "foreign_uploader":
        assert "other_person_record" in plan.blockers
    else:
        assert not plan.blockers
        if state == "active":
            monkeypatch.setattr(
                "ase.adapters.persistence.private_removal_selection.MAX_BYTES", 4095
            )
            assert (
                "removal_inventory_limit_use_smaller_scopes"
                in (await preview(container, admin, request)).blockers
            )
            monkeypatch.undo()
        await apply(container, admin, request, plan.fingerprint)
        async with container.session_factory() as session:
            assert await session.get(OriginalAssetRow, asset.id) is None


async def test_shared_copies_are_preserved_and_cannot_be_targeted_as_private(
    container, user, admin
):
    await authorise(container, admin, user)
    async with team_service(container) as service:
        team = await service.create(user, "Shared desk", CONTEXT)
    original, version = await report(container, user)
    shared, _ = await report(container, user, team_id=team.id)
    provenance = ReportTeamCopyRow(
        id=uuid4(),
        report_id=shared.id,
        team_id=team.id,
        source_report_id=original.id,
        source_version_id=version.id,
        source_version_number=1,
        copied_by=user.id,
        copied_at=container.clock.now(),
        content_sha256="a" * 64,
        disclosed_labels=[],
        omissions=[],
    )
    await seed(container, provenance)
    with pytest.raises(NotFound):
        await preview(container, admin, RemovalRequest(user.id, RemovalScope.REPORT, shared.id))
    request = RemovalRequest(user.id, RemovalScope.REPORT, original.id)
    plan = await preview(container, admin, request)
    assert not plan.blockers
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        assert await session.get(ReportRow, shared.id) is not None
        assert await session.get(ReportTeamCopyRow, provenance.id) is not None


async def test_account_graph_overflow_requires_smaller_scopes(container, user, admin, monkeypatch):
    await authorise(container, admin, user, inactive=True)
    await report(container, user)
    await report(container, user)
    monkeypatch.setattr("ase.adapters.persistence.private_removal_graph.MAX_ROOTS", 1)
    plan = await preview(container, admin, RemovalRequest(user.id, RemovalScope.ACCOUNT))
    assert "graph_limit_use_individual_saved_work_scopes" in plan.blockers
