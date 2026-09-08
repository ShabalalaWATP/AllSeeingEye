"""Real0031 PostgreSQL migrations retain selected history and reject unsafe rollback."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

from ase.adapters.persistence.base import Base
from ase.infrastructure.migrations import alembic_config
from test_annotation_monitor_migration import TABLES
from test_annotation_monitor_migration_postgres import (
    database_url as database_url,  # noqa: PLC0414
)
from test_annotation_monitor_migration_postgres import seed_alerts, snapshot


def retained_values(table):
    values = {}
    for column in table.c:
        if column.nullable:
            values[column.name] = None
        elif isinstance(column.type, sa.Uuid):
            values[column.name] = uuid4()
        elif isinstance(column.type, sa.Boolean):
            values[column.name] = True
        elif isinstance(column.type, sa.Integer):
            values[column.name] = 1
        elif isinstance(column.type, sa.DateTime):
            values[column.name] = datetime(2026, 9, 8, tzinfo=UTC)
        elif isinstance(column.type, sa.JSON):
            values[column.name] = ["claim"]
        else:
            values[column.name] = "retained"
    return values


def retained_selected_history(connection):
    """Synthetic retained payloads test byte preservation, not domain payload replay."""
    seed_alerts(connection)
    metadata = sa.MetaData()
    metadata.reflect(connection)
    owner = connection.scalar(sa.select(metadata.tables["users"].c.id))
    report = connection.scalar(sa.select(metadata.tables["reports"].c.id))
    monitor, root, previous, revision, transition, alert = (uuid4() for _ in range(6))
    for name in (
        "annotation_monitors",
        "annotation_monitor_watches",
        "annotation_revision_outbox",
        "annotation_monitor_transitions",
    ):
        table = metadata.tables[name]
        values = retained_values(table)
        if name == "annotation_monitors":
            values.update(id=monitor, created_by=owner, report_id=report, status="active")
        else:
            values.update(monitor_id=monitor, kind="claim")
        if name == "annotation_monitor_watches":
            values.update(root_id=root, revision_id=previous)
        elif name == "annotation_revision_outbox":
            values.update(root_id=root, previous_revision_id=previous, revision_id=revision)
        elif name == "annotation_monitor_transitions":
            values.update(id=transition, alert_id=alert)
        connection.execute(table.insert().values(**values))
    alerts = metadata.tables["alerts"]
    sample = dict(connection.execute(sa.select(alerts).limit(1)).mappings().one())
    sample.update(
        id=alert,
        indicator_id=None,
        schedule_id=None,
        annotation_monitor_id=monitor,
        annotation_transition_id=transition,
    )
    connection.execute(alerts.insert().values(**sample))


def parity(connection):
    context = MigrationContext.configure(
        connection,
        opts={
            "include_object": lambda obj, name, kind, reflected, comparison: (
                kind != "table" or name in TABLES | {"alerts"}
            ),
        },
    )
    assert compare_metadata(context, Base.metadata) == []
    columns = {
        c["name"]: c for c in sa.inspect(connection).get_columns("annotation_revision_outbox")
    }
    assert columns["previous_revision_id"]["nullable"] is True


async def test_postgres0031_preserves_selected_history_acknowledgements_and_roundtrip(database_url):
    config = alembic_config(database_url)
    await asyncio.to_thread(command.upgrade, config, "0030")
    engine = create_async_engine(database_url, poolclass=sa.NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(retained_selected_history)
            columns, before = await connection.run_sync(snapshot)
        assert len(before["alerts"]) == 3
        assert all(row["acknowledged_by"] and row["acknowledged_at"] for row in before["alerts"])
        for _ in range(2):
            await asyncio.to_thread(command.upgrade, config, "0031")
            async with engine.connect() as connection:
                await connection.run_sync(parity)
                assert (await connection.run_sync(lambda sync: snapshot(sync, columns)))[
                    1
                ] == before
                assert (
                    await connection.execute(
                        sa.text("SELECT mode, inventory_overflow FROM annotation_monitors")
                    )
                ).all() == [("selected_roots", False)]
            await asyncio.to_thread(command.downgrade, config, "0030")
            async with engine.connect() as connection:
                assert await connection.run_sync(snapshot) == (columns, before)
                nullable = await connection.run_sync(
                    lambda sync: {
                        c["name"]: c["nullable"]
                        for c in sa.inspect(sync).get_columns("annotation_revision_outbox")
                    }
                )
                assert nullable["previous_revision_id"] is False
    finally:
        await engine.dispose()


@pytest.mark.parametrize("retained", ["inventory", "overflow", "creation", "orphan_creation"])
async def test_postgres0031_refuses_unsafe_downgrade_before_data_or_schema_changes(
    database_url, retained
):
    config = alembic_config(database_url)
    await asyncio.to_thread(command.upgrade, config, "0030")
    engine = create_async_engine(database_url, poolclass=sa.NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(retained_selected_history)
        await asyncio.to_thread(command.upgrade, config, "0031")
        async with engine.begin() as connection:
            if retained == "inventory":
                await connection.execute(
                    sa.text("UPDATE annotation_monitors SET mode='report_inventory'")
                )
            elif retained == "overflow":
                await connection.execute(
                    sa.text("UPDATE annotation_monitors SET inventory_overflow=true")
                )
            else:
                await connection.execute(
                    sa.text("UPDATE annotation_revision_outbox SET previous_revision_id=NULL")
                )
                if retained == "orphan_creation":
                    # Deliberate damaged storage in an owned disposable database only.
                    await connection.execute(sa.text("SET LOCAL session_replication_role=replica"))
                    await connection.execute(sa.text("DELETE FROM annotation_monitors"))
            before = await connection.run_sync(snapshot)
        with pytest.raises(RuntimeError, match="Refusing downgrade"):
            await asyncio.to_thread(command.downgrade, config, "0030")
        async with engine.connect() as connection:
            assert await connection.run_sync(snapshot) == before
            await connection.run_sync(parity)
            assert (
                await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                == "0031"
            )
    finally:
        await engine.dispose()
