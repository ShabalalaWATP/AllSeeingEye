"""Opt-in migration parity on a separate, synthetic PostgreSQL database."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _assert_audit_readable, _insert


@asynccontextmanager
async def _disposable_database() -> AsyncIterator[str]:
    source = os.environ.get("ASE_SCOPE_MIGRATION_POSTGRES_URL") or os.environ.get(
        "ASE_TEST_DATABASE_URL"
    )
    if not source:
        pytest.skip("Set ASE_SCOPE_MIGRATION_POSTGRES_URL to a disposable PostgreSQL server")
    url = sa.make_url(source)
    if url.get_backend_name() != "postgresql":
        pytest.skip("The configured test database is not PostgreSQL")
    assert url.drivername == "postgresql+asyncpg"
    # Only this generated database is created/dropped; the supplied database is retained.
    name = f"ase_scope_migration_{uuid4().hex}"
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
        try:
            yield url.set(database=name).render_as_string(hide_password=False)
        finally:
            async with engine.connect() as connection:
                await connection.execute(sa.text(f'DROP DATABASE "{name}"'))
    finally:
        await engine.dispose()


def _seed(connection: sa.Connection) -> dict[str, object]:
    metadata = sa.MetaData()
    metadata.reflect(connection)
    tables = metadata.tables
    owner = _insert(connection, tables["users"], email="one@example.com", role="user")
    other = _insert(connection, tables["users"], email="two@example.com", role="user")
    aoi = _insert(connection, tables["aois"], created_by=owner)
    plan = _insert(connection, tables["collection_plans"], created_by=other, aoi_id=aoi)
    indicator = _insert(connection, tables["indicators"], created_by=owner, plan_id=plan)
    report = _insert(connection, tables["reports"], created_by=owner, scope={"plan": plan})
    _insert(
        connection,
        tables["report_versions"],
        report_id=report,
        evidence=[{"id": "frozen", "hash": "unaltered"}],
        body={"summary": "Historical"},
    )
    schedule = _insert(connection, tables["schedules"], created_by=owner, plan_id=plan)
    alert = _insert(connection, tables["alerts"], indicator_id=indicator, report_id=report)
    orphan = _insert(connection, tables["alerts"], indicator_id=uuid4().hex)
    return {
        "roots": {
            "aois": aoi,
            "collection_plans": plan,
            "indicators": indicator,
            "reports": report,
            "schedules": schedule,
        },
        "owner": owner,
        "alert": alert,
        "orphan": orphan,
        "version": dict(connection.execute(sa.select(tables["report_versions"])).mappings().one()),
    }


def _verify(connection: sa.Connection, original: dict[str, Any], *, upgraded: bool) -> None:
    metadata = sa.MetaData()
    metadata.reflect(connection)
    tables = metadata.tables
    assert (
        dict(connection.execute(sa.select(tables["report_versions"])).mappings().one())
        == original["version"]
    )
    entries = connection.execute(sa.select(tables["audit_log"])).mappings().all()
    assert len(entries) == 5
    assert all(entry["action"] == "legacy_scope_conflict" for entry in entries)
    for table, identifier in original["roots"].items():
        row = connection.execute(sa.select(tables[table])).mappings().one()
        assert row["id"] == UUID(identifier)
        if upgraded:
            assert row["team_id"] is None
            assert any(
                fk["referred_table"] == "teams"
                for fk in sa.inspect(connection).get_foreign_keys(table)
            )
        else:
            assert "team_id" not in tables[table].c
    if not upgraded:
        assert "created_by" not in tables["alerts"].c
        return
    alerts = {row["id"]: row for row in connection.execute(sa.select(tables["alerts"])).mappings()}
    assert alerts[UUID(original["alert"])]["created_by"] == UUID(original["owner"])
    assert alerts[UUID(original["orphan"])]["created_by"] is None
    assert all(row["team_id"] is None for row in alerts.values())
    assert {entry["details"]["reason"] for entry in entries} == {
        "missing_target",
        "different_personal_owner",
    }
    assert all(
        set(entry["details"])
        == {"source_table", "source_id", "target_table", "target_id", "reason"}
        for entry in entries
    )


async def test_postgres_scope_migration_preserves_legacy_data_and_decodable_audit() -> None:
    async with _disposable_database() as url:
        config = alembic_config(url)
        await asyncio.to_thread(command.upgrade, config, "0013")
        engine = create_async_engine(url)
        try:
            async with engine.begin() as connection:
                original = await connection.run_sync(_seed)
            await asyncio.to_thread(command.upgrade, config, "0014")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _verify(sync, original, upgraded=True))
            await _assert_audit_readable(url)
            await asyncio.to_thread(command.downgrade, config, "0013")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _verify(sync, original, upgraded=False))
        finally:
            await engine.dispose()
