"""Teams, directory, board and AI usage migrations 0045 onwards on real PostgreSQL."""

import asyncio
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from ase.adapters.persistence.base import Base
from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert

NOW = datetime(2026, 9, 15, 9, tzinfo=UTC)


@pytest.fixture
async def database_url():
    source = os.environ.get("ASE_TEAMS_MIGRATION_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_TEAMS_MIGRATION_POSTGRES_URL to a disposable PG server")
    url = sa.make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_teams_migration_{uuid4().hex}"
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
        try:
            yield url.set(database=name).render_as_string(hide_password=False)
        finally:
            async with admin.connect() as connection:
                await connection.execute(sa.text(f'DROP DATABASE "{name}"'))
    finally:
        await admin.dispose()


async def _migrate(step, config, revision: str) -> None:
    await asyncio.to_thread(step, config, revision)


def _tables(connection: sa.Connection) -> dict[str, sa.Table]:
    metadata = sa.MetaData()
    metadata.reflect(connection)
    return dict(metadata.tables)


def _seed_legacy_authority(connection: sa.Connection) -> dict[str, str]:
    """Accounts and teams as they stood at 0044, before membership-only authority."""
    tables = _tables(connection)
    users, teams, members = tables["users"], tables["teams"], tables["team_memberships"]
    ids = {
        key: _insert(
            connection,
            users,
            email=f"{key}@example.com",
            display_name=key.title(),
            role=role,
            is_active=True,
            security_version=4,
        )
        for key, role in (("legacy", "manager"), ("ordinary", "user"), ("admin", "admin"))
    }
    ids["led"] = _insert(
        connection, teams, name="Led desk", is_active=True, created_by=ids["legacy"]
    )
    ids["dormant"] = _insert(
        connection, teams, name="Dormant desk", is_active=True, created_by=ids["ordinary"]
    )
    ids["founded"] = _insert(
        connection, teams, name="Admin desk", is_active=True, created_by=ids["admin"]
    )
    for team, user, role in (
        ("led", "legacy", "manager"),
        ("led", "ordinary", "manager"),
        ("dormant", "ordinary", "manager"),
    ):
        connection.execute(
            members.insert().values(team_id=ids[team], user_id=ids[user], role=role, joined_at=NOW)
        )
    return ids


def _authority_after_upgrade(connection: sa.Connection, ids: dict[str, str]) -> None:
    tables = _tables(connection)
    users, members, audit = tables["users"], tables["team_memberships"], tables["audit_log"]
    legacy = connection.execute(
        sa.select(users.c.role, users.c.security_version).where(users.c.id == ids["legacy"])
    ).one()
    assert (legacy.role, legacy.security_version) == ("user", 5)
    roles = {
        (str(row.team_id).replace("-", ""), str(row.user_id).replace("-", "")): row.role
        for row in connection.execute(sa.select(members))
    }
    assert roles[(ids["led"], ids["legacy"])] == "manager"
    # An ordinary account's Manager membership carried no authority before 0050.
    assert roles[(ids["led"], ids["ordinary"])] == "member"
    assert roles[(ids["dormant"], ids["ordinary"])] == "member"
    # 0047 gives an active creator their team, recorded in the audit inventory.
    assert roles[(ids["founded"], ids["admin"])] == "manager"
    details = connection.execute(
        sa.select(audit.c.subject, audit.c.details).where(
            audit.c.action == "team_authority_migrated"
        )
    ).all()
    subjects = {row.subject for row in details}
    assert f"team:{UUID(ids['dormant'])}" in subjects
    assert all("@" not in str(row.details) for row in details)


def _models_match(connection: sa.Connection) -> None:
    context = MigrationContext.configure(connection)
    assert compare_metadata(context, Base.metadata) == []


def _partial_unique_indexes_hold(connection: sa.Connection, ids: dict[str, str]) -> None:
    tables = _tables(connection)
    invitations, policies = tables["team_invitations"], tables["ai_usage_policies"]
    pending = {
        "team_id": ids["founded"],
        "recipient_id": ids["ordinary"],
        "inviter_id": ids["admin"],
        "role": "member",
        "status": "pending",
        "created_at": NOW,
        "expires_at": NOW,
    }
    with connection.begin_nested():
        connection.execute(invitations.insert().values(id=uuid4(), **pending))
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        connection.execute(invitations.insert().values(id=uuid4(), **pending))
    # Non-pending history may repeat for the same pair.
    with connection.begin_nested():
        connection.execute(
            invitations.insert().values(id=uuid4(), **{**pending, "status": "declined"})
        )
    site = {
        "scope": "global",
        "target_id": None,
        "period": "month",
        "enabled": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    with connection.begin_nested():
        connection.execute(policies.insert().values(id=uuid4(), **site))
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        connection.execute(policies.insert().values(id=uuid4(), **site))
    with connection.begin_nested():
        connection.execute(policies.insert().values(id=uuid4(), **{**site, "enabled": False}))


def _retained_counts(connection: sa.Connection) -> dict[str, int]:
    tables = _tables(connection)
    return {
        name: connection.scalar(sa.select(sa.func.count()).select_from(tables[name])) or 0
        for name in ("team_invitations", "ai_usage_policies")
    }


def _clear_retained(connection: sa.Connection) -> None:
    tables = _tables(connection)
    for name in ("team_invitations", "ai_usage_policies"):
        connection.execute(tables[name].delete())


async def _run(connection: AsyncConnection, fn, *args):
    result = await connection.run_sync(fn, *args)
    await connection.commit()
    return result


async def test_teams_and_usage_migrations_round_trip_on_postgres(database_url):
    config = alembic_config(database_url)
    await _migrate(command.upgrade, config, "0044")
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            ids = await _run(connection, _seed_legacy_authority)
        await _migrate(command.upgrade, config, "head")
        async with engine.connect() as connection:
            await _run(connection, _authority_after_upgrade, ids)
            await _run(connection, _models_match)
            await _run(connection, _partial_unique_indexes_hold, ids)
            assert await _run(connection, _retained_counts) == {
                "team_invitations": 2,
                "ai_usage_policies": 2,
            }
        # Guards refuse to discard retained invitations or allowance records.
        with pytest.raises(RuntimeError, match="records remain"):
            await _migrate(command.downgrade, config, "0044")
        async with engine.connect() as connection:
            await _run(connection, _clear_retained)
        await _migrate(command.downgrade, config, "0044")
        async with engine.connect() as connection:
            names = await connection.run_sync(lambda sync: set(sa.inspect(sync).get_table_names()))
        assert not {"team_invitations", "ai_usage_policies", "directory_avatars"} & names
        assert "team_memberships" in names
        await _migrate(command.upgrade, config, "head")
        async with engine.connect() as connection:
            await _run(connection, _models_match)
    finally:
        await engine.dispose()
