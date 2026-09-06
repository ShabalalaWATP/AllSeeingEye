"""Immutable map storage, conditional appends and visibility before SQL pagination."""

import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import event, func, select, update

from ase.adapters.persistence.map_view_models import MapViewRevisionRow, MapViewRow
from ase.adapters.persistence.map_views import SqlMapViewRepository
from ase.adapters.persistence.models import ReportRow
from ase.container import Container
from ase.domain.access import Visibility
from ase.domain.map_view_records import revision_bytes, revision_digest
from ase.domain.map_views import MapCamera, MapView, MapViewRevision, MapViewState
from ase.domain.users import User
from report_documents_helpers import document_records
from test_mfa_migration import prepare
from test_report_team_scope import team_for


async def seed(container: Container, owner: User, team_id: UUID | None = None):
    report, version = document_records(owner.id)
    report.team_id = team_id
    state = MapViewState(MapCamera(179, 60, 4), source_ids=("example",), selected_evidence="E1")
    view_id, revision_id = uuid4(), uuid4()
    view = MapView(view_id, report.id, owner.id, team_id, revision_id, container.clock.now())
    revision = MapViewRevision(
        revision_id,
        view_id,
        1,
        "Saved 地图",
        version.id,
        version.number,
        state,
        "e" * 64,
        revision_digest(state, "Saved 地图", str(version.id), "e" * 64),
        owner.id,
        container.clock.now(),
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(report, version)
        await SqlMapViewRepository(session).create(view, revision)
        await session.commit()
    return view, revision


async def test_exact_revision_roundtrip_and_stale_append_never_changes_history(
    container: Container,
    user: User,
) -> None:
    view, original = await seed(container, user)
    next_revision = replace(original, id=uuid4(), number=2, title="Second view")
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        assert await repository.revision(view.id, original.id) == original
        assert await repository.revision(uuid4(), original.id) is None
        assert await repository.get(uuid4()) is None
        assert await repository.append(next_revision, original.id)
        await session.commit()
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        stale = replace(next_revision, id=uuid4(), title="Stale tab")
        assert not await repository.append(stale, original.id)
        await session.commit()
        assert await repository.revision(view.id, stale.id) is None
        assert await repository.revision(view.id, original.id) == original
        assert await repository.revision(view.id, next_revision.id) == next_revision
        assert (await repository.get(view.id)).latest_revision_id == next_revision.id
        assert await session.scalar(select(func.count()).select_from(MapViewRevisionRow)) == 2


async def test_archive_retains_usage_and_history_but_disallows_appends(
    container: Container,
    user: User,
) -> None:
    view, original = await seed(container, user)
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        expected = (1, revision_bytes(original.state, original.title))
        assert await repository.scope_usage(user.id, None) == expected
        await repository.archive(view.id)
        await session.commit()
        assert await repository.scope_usage(user.id, None) == expected
        assert (await repository.get(view.id)).archived
        assert await repository.revision(view.id, original.id) == original
        assert not await repository.append(replace(original, id=uuid4(), number=2), original.id)
        page = await repository.list_visible(Visibility(user.id, False, ()), view.report_id, 10, 0)
        assert page.total == 0 and page.items == ()


async def test_appending_rolls_back_pointer_and_revision_together(
    container: Container,
    user: User,
) -> None:
    view, original = await seed(container, user)
    candidate = replace(original, id=uuid4(), number=2)
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        assert await repository.append(candidate, original.id)
        await session.rollback()
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        assert (await repository.get(view.id)).latest_revision_id == original.id
        assert await repository.revision(view.id, candidate.id) is None
        assert await repository.scope_usage(user.id, None) == (
            1,
            revision_bytes(original.state, original.title),
        )


async def test_parent_and_view_visibility_each_filter_before_counts_and_limits(
    container: Container,
    user: User,
    admin: User,
) -> None:
    view, original = await seed(container, user)
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        visible = Visibility(user.id, False, ())
        page = await repository.list_visible(visible, view.report_id, 1, 0)
        assert page.total == 1
        assert page.items[0].title == original.title
        assert (await repository.list_visible(visible, view.report_id, 1, 1)).items == ()
        # Simulate inconsistent stored scope: either side must independently deny visibility.
        await session.execute(
            update(ReportRow).where(ReportRow.id == view.report_id).values(created_by=admin.id)
        )
        assert (await repository.list_visible(visible, view.report_id, 1, 0)).total == 0
        await session.execute(
            update(ReportRow).where(ReportRow.id == view.report_id).values(created_by=user.id)
        )
        await session.execute(
            update(MapViewRow).where(MapViewRow.id == view.id).values(created_by=admin.id)
        )
        assert (await repository.list_visible(visible, view.report_id, 1, 0)).total == 0
        assert (
            await repository.list_visible(Visibility(admin.id, True, ()), view.report_id, 1, 0)
        ).total == 1


async def test_summary_queries_never_load_canonical_geometry(
    container: Container,
    user: User,
) -> None:
    view, revision = await seed(container, user)
    statements: list[str] = []

    def record_statement(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(container.engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        async with container.session_factory() as session:
            page = await SqlMapViewRepository(session).list_visible(
                Visibility(user.id, False, ()),
                view.report_id,
                1,
                0,
            )
        assert page.total == 1 and page.items[0].title == revision.title
        assert statements
        assert all("map_view_revisions.state" not in statement for statement in statements)
    finally:
        event.remove(container.engine.sync_engine, "before_cursor_execute", record_statement)


async def test_team_usage_is_shared_and_revocation_filters_the_report_view(
    container: Container,
    user: User,
    admin: User,
) -> None:
    team = await team_for(container, admin, user)
    view, revision = await seed(container, user, team.id)
    other, other_revision = await seed(container, admin, team.id)
    await seed(container, user)
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        usage = (
            2,
            revision_bytes(revision.state, revision.title)
            + revision_bytes(other_revision.state, other_revision.title),
        )
        assert await repository.scope_usage(user.id, team.id) == usage
        assert await repository.scope_usage(admin.id, team.id) == usage
        assert (await repository.scope_usage(admin.id, None)) == (0, 0)
        assert (
            await repository.list_visible(
                Visibility(user.id, False, (team.id,)), other.report_id, 1, 0
            )
        ).total == 1
        assert (
            await repository.list_visible(Visibility(user.id, False, ()), view.report_id, 1, 0)
        ).total == 0


async def test_revision_number_and_report_version_anchor_cannot_be_mismatched(
    container: Container,
    user: User,
) -> None:
    view, original = await seed(container, user)
    _, foreign = await seed(container, user)
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        assert not await repository.append(replace(original, id=uuid4(), number=3), original.id)
        assert not await repository.append(
            replace(original, id=uuid4(), number=2, report_version_id=foreign.report_version_id),
            original.id,
        )
        assert not await repository.append(
            replace(original, id=uuid4(), number=2, report_version_number=2), original.id
        )
        for invalid in (
            replace(original, number=2),
            replace(original, view_id=uuid4()),
            replace(original, id=uuid4()),
        ):
            with pytest.raises(ValueError, match="Initial map revision"):
                await repository.create(view, invalid)
        new_id, new_revision_id = uuid4(), uuid4()
        with pytest.raises(ValueError, match="exact parent report version"):
            await repository.create(
                replace(view, id=new_id, latest_revision_id=new_revision_id),
                replace(
                    original,
                    id=new_revision_id,
                    view_id=new_id,
                    report_version_id=foreign.report_version_id,
                ),
            )
        assert (await repository.get(view.id)).latest_revision_id == original.id
        assert await repository.get(new_id) is None


async def test_explicit_cleanup_only_removes_the_selected_reports_maps(
    container: Container,
    user: User,
) -> None:
    view, original = await seed(container, user)
    kept, kept_revision = await seed(container, user)
    async with container.session_factory() as session:
        repository = SqlMapViewRepository(session)
        await repository.archive(view.id)
        await repository.delete_for_report(view.report_id)
        await session.commit()
        assert await repository.get(view.id) is None
        assert await repository.revision(view.id, original.id) is None
        assert await repository.revision(kept.id, kept_revision.id) == kept_revision
        assert await session.get(ReportRow, view.report_id) is not None


def test_migration_preserves_accounts_and_refuses_lossy_downgrade(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0024")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT id FROM users").fetchone() == (identity,)
        assert connection.execute("SELECT count(*) FROM map_views").fetchone() == (0,)
    command.downgrade(config, "0023")
    command.upgrade(config, "0024")
    # Synthetic rows in a disposable database, no operator records or credentials.
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO map_views VALUES (?,?,?,?,?,?,?)",
            (
                "a" * 32,
                "b" * 32,
                identity,
                None,
                "c" * 32,
                "2026-09-06T12:00:00Z",
                True,
            ),
        )
    with pytest.raises(RuntimeError, match="Saved map revisions remain"):
        command.downgrade(config, "0023")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT count(*) FROM map_views").fetchone() == (1,)
