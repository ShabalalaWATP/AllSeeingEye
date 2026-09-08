"""Real PostgreSQL0030 migrations preserve old alerts and refuse retained monitor history."""

import asyncio
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

from ase.adapters.persistence.base import Base
from ase.infrastructure.migrations import alembic_config
from test_annotation_monitor_migration import TABLES
from test_llm_connections_migration import _seed


@pytest.fixture
async def database_url():
    source = os.environ.get("ASE_MONITOR_MIGRATION_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_MONITOR_MIGRATION_POSTGRES_URL to a disposable PG server")
    url = sa.make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_monitor_migration_{uuid4().hex}"
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


def seed_alerts(connection):
    owner = UUID(str(_seed(connection)["owner"]))
    alerts = sa.Table("alerts", sa.MetaData(), autoload_with=connection)
    for origin in ("indicator", "schedule"):
        connection.execute(
            alerts.insert().values(
                id=uuid4(),
                indicator_id=uuid4() if origin == "indicator" else None,
                schedule_id=uuid4() if origin == "schedule" else None,
                fired_at=datetime(2026, 9, 7, 12, tzinfo=UTC),
                title=origin,
                summary="Preserve acknowledged public-source alert",
                count=1,
                threshold=1,
                event_ids=["frozen-event"],
                countries=["GB"],
                acknowledged_at=datetime(2026, 9, 7, 12, 1, tzinfo=UTC),
                acknowledged_by=owner,
                created_by=owner,
            )
        )


def snapshot(connection, columns=None):
    metadata = sa.MetaData()
    metadata.reflect(connection)
    selected = columns or {
        name: list(table.c.keys())
        for name, table in metadata.tables.items()
        if name != "alembic_version"
    }
    rows = {
        name: sorted(
            [
                dict(row)
                for row in connection.execute(
                    sa.select(*(metadata.tables[name].c[column] for column in names))
                ).mappings()
            ],
            key=repr,
        )
        for name, names in selected.items()
    }
    return selected, rows


def schema_parity(connection):
    context = MigrationContext.configure(
        connection,
        opts={
            "include_object": lambda obj, name, kind, reflected, comparison: (
                kind != "table" or name in TABLES | {"alerts"}
            )
        },
    )
    # Historical0030 must be compared with its own schema, before inventory0031.
    historical = sa.MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(historical)
    monitors = historical.tables["annotation_monitors"]
    for name in ("mode", "inventory_overflow"):
        monitors._columns.remove(monitors.c[name])
    historical.tables["annotation_revision_outbox"].c.previous_revision_id.nullable = False
    assert compare_metadata(context, historical) == []
    inspector = sa.inspect(connection)
    assert "ck_alerts_one_origin" in {
        row["name"] for row in inspector.get_check_constraints("alerts")
    }
    assert "uq_alerts_annotation_transition_id" in {
        row["name"] for row in inspector.get_unique_constraints("alerts")
    }


async def invalid_alert_origins(connection):
    table = await connection.run_sync(
        lambda sync: sa.Table("alerts", sa.MetaData(), autoload_with=sync)
    )
    alert_id = await connection.scalar(
        sa.select(table.c.id).where(table.c.indicator_id.is_not(None))
    )
    for changes in (
        {"indicator_id": None},
        {"schedule_id": uuid4()},
        {"annotation_transition_id": uuid4()},
        {"indicator_id": None, "annotation_monitor_id": uuid4()},
    ):
        transaction = await connection.begin_nested()
        try:
            with pytest.raises(sa.exc.IntegrityError):
                await connection.execute(
                    table.update().where(table.c.id == alert_id).values(**changes)
                )
        finally:
            await transaction.rollback()


async def test_postgres0030_preserves_acknowledged_origins_and_roundtrips(database_url):
    config = alembic_config(database_url)
    await asyncio.to_thread(command.upgrade, config, "0029")
    engine = create_async_engine(database_url, poolclass=sa.NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(seed_alerts)
            columns, before = await connection.run_sync(snapshot)
        assert len(before["alerts"]) == 2 and before["reports"] and before["report_versions"]
        assert all(row["acknowledged_at"] and row["acknowledged_by"] for row in before["alerts"])
        await asyncio.to_thread(command.upgrade, config, "0030")
        async with engine.connect() as connection:
            await connection.run_sync(schema_parity)
            assert (await connection.run_sync(lambda sync: snapshot(sync, columns)))[1] == before
            assert (
                await connection.execute(
                    sa.text("SELECT annotation_monitor_id, annotation_transition_id FROM alerts")
                )
            ).all() == [(None, None), (None, None)]
            await invalid_alert_origins(connection)
        await asyncio.to_thread(command.downgrade, config, "0029")
        async with engine.connect() as connection:
            assert await connection.run_sync(snapshot) == (columns, before)
            assert (
                await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                == "0029"
            )
        await asyncio.to_thread(command.upgrade, config, "0030")
        async with engine.connect() as connection:
            await connection.run_sync(schema_parity)
            assert (await connection.run_sync(lambda sync: snapshot(sync, columns)))[1] == before
            assert (
                await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                == "0030"
            )
    finally:
        await engine.dispose()


def insert_damaged_history(connection, name):
    table = sa.Table(name, sa.MetaData(), autoload_with=connection)
    values = {}
    for column in table.c:
        if column.nullable:
            values[column.name] = None
        elif isinstance(column.type, sa.Uuid):
            values[column.name] = uuid4()
        elif isinstance(column.type, sa.Boolean):
            values[column.name] = False
        elif isinstance(column.type, sa.Integer):
            values[column.name] = 1
        elif isinstance(column.type, sa.DateTime):
            values[column.name] = datetime(2026, 9, 7, tzinfo=UTC)
        elif isinstance(column.type, sa.JSON):
            values[column.name] = []
        else:
            values[column.name] = "retained"
    # Owned disposable schema only: retain orphan rows to exercise each guard separately.
    connection.execute(sa.text("SET LOCAL session_replication_role = replica"))
    connection.execute(table.insert().values(**values))


@pytest.mark.parametrize("retained", [*sorted(TABLES), "damaged_alert"])
async def test_postgres0030_refuses_every_retained_history_origin_without_ddl(
    database_url, retained
):
    config = alembic_config(database_url)
    await asyncio.to_thread(command.upgrade, config, "0029")
    engine = create_async_engine(database_url, poolclass=sa.NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(seed_alerts)
        await asyncio.to_thread(command.upgrade, config, "0030")
        async with engine.begin() as connection:
            if retained == "damaged_alert":
                # PostgreSQL cannot disable CHECKs like SQLite. Deliberately simulate damaged
                # history in this owned database, then prove downgrade does not destroy it.
                await connection.execute(
                    sa.text("ALTER TABLE alerts DROP CONSTRAINT ck_alerts_one_origin")
                )
                await connection.execute(
                    sa.text(
                        "UPDATE alerts SET annotation_transition_id = :transition "
                        "WHERE indicator_id IS NOT NULL"
                    ),
                    {"transition": uuid4()},
                )
            else:
                await connection.run_sync(lambda sync: insert_damaged_history(sync, retained))
            before = await connection.run_sync(snapshot)
            checks = await connection.run_sync(
                lambda sync: sa.inspect(sync).get_check_constraints("alerts")
            )
        with pytest.raises(RuntimeError, match="Refusing downgrade"):
            await asyncio.to_thread(command.downgrade, config, "0029")
        async with engine.connect() as connection:
            assert await connection.run_sync(snapshot) == before
            assert (
                await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                == "0030"
            )
            assert (
                await connection.run_sync(
                    lambda sync: sa.inspect(sync).get_check_constraints("alerts")
                )
                == checks
            )
    finally:
        await engine.dispose()
