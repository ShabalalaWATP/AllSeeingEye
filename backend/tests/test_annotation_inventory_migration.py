"""SQLite0031 retains every selected-state byte and refuses unsafe downgrade."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from ase.adapters.persistence.base import Base
from test_annotation_monitor_migration import TABLES, prepared


def database_0030(tmp_path):
    config, database, owner = prepared(tmp_path)
    command.upgrade(config, "0030")
    engine = sa.create_engine(f"sqlite:///{database}")
    monitor = uuid4().hex
    try:
        with engine.begin() as connection:
            for name in (
                "annotation_monitors",
                "annotation_monitor_watches",
                "annotation_revision_outbox",
                "annotation_monitor_transitions",
            ):
                table = sa.Table(name, sa.MetaData(), autoload_with=connection)
                values = {}
                for column in table.c:
                    if column.nullable:
                        values[column.name] = None
                    elif isinstance(column.type, sa.Boolean):
                        values[column.name] = True
                    elif isinstance(column.type, sa.Integer):
                        values[column.name] = 1
                    elif isinstance(column.type, sa.DateTime):
                        values[column.name] = datetime(2026, 9, 8, tzinfo=UTC)
                    elif isinstance(column.type, sa.JSON):
                        values[column.name] = ["claim"]
                    else:
                        values[column.name] = uuid4().hex
                if name == "annotation_monitors":
                    values.update(
                        id=monitor,
                        created_by=owner,
                        status="active",
                        checkpoint_payload="retained checkpoint bytes",
                    )
                else:
                    values.update(monitor_id=monitor, kind="claim")
                if name == "annotation_monitor_transitions":
                    values.update(
                        payload="retained immutable comparison bytes", payload_sha256="a" * 64
                    )
                connection.execute(table.insert().values(**values))
    finally:
        engine.dispose()
    return config, database


def snapshot(database, columns=None):
    with closing(sqlite3.connect(database)) as connection:
        if columns is None:
            columns = {
                name: [r[1] for r in connection.execute(f"PRAGMA table_info({name})")]
                for name in sorted(TABLES | {"alerts", "users"})
            }
        return columns, {
            name: connection.execute(
                f"SELECT {','.join(names)} FROM {name} ORDER BY 1"  # noqa: S608 (fixed migration schema)
            ).fetchall()
            for name, names in columns.items()
        }


def test_sqlite0031_preserves_selected_state_and_roundtrip(tmp_path):
    config, database = database_0030(tmp_path)
    columns, before = snapshot(database)
    for _ in range(2):
        command.upgrade(config, "0031")
        assert snapshot(database, columns)[1] == before
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute(
                "SELECT mode,inventory_overflow FROM annotation_monitors"
            ).fetchall() == [("selected_roots", 0)]
        engine = sa.create_engine(f"sqlite:///{database}")
        try:
            with engine.connect() as connection:
                context = MigrationContext.configure(
                    connection,
                    opts={
                        "include_object": lambda obj, name, kind, reflected, comparison: (
                            kind != "table" or name in TABLES | {"alerts"}
                        )
                    },
                )
                assert compare_metadata(context, Base.metadata) == []
        finally:
            engine.dispose()
        command.downgrade(config, "0030")
        assert snapshot(database) == (columns, before)


@pytest.mark.parametrize("retained", ["inventory", "overflow", "creation", "orphan_creation"])
def test_sqlite0031_refuses_unsafe_state_without_changing_any_byte(tmp_path, retained):
    config, database = database_0030(tmp_path)
    command.upgrade(config, "0031")
    with closing(sqlite3.connect(database)) as connection, connection:
        if retained == "inventory":
            connection.execute("UPDATE annotation_monitors SET mode='report_inventory'")
        elif retained == "overflow":
            connection.execute("UPDATE annotation_monitors SET inventory_overflow=1")
        else:
            connection.execute("UPDATE annotation_revision_outbox SET previous_revision_id=NULL")
            if retained == "orphan_creation":
                connection.execute("DELETE FROM annotation_monitors")
    before = snapshot(database)
    with pytest.raises(RuntimeError, match="Refusing downgrade"):
        command.downgrade(config, "0030")
    assert snapshot(database) == before
