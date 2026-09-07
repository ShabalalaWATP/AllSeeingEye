"""Disposable SQLite0030 preservation, parity and refusal before destructive downgrade."""

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
from test_mfa_migration import prepare

TABLES = {
    "annotation_monitors",
    "annotation_monitor_watches",
    "annotation_revision_outbox",
    "annotation_monitor_transitions",
}


def prepared(tmp_path):
    config, database, owner = prepare(tmp_path)
    command.upgrade(config, "0029")
    with closing(sqlite3.connect(database)) as connection, connection:
        for origin in ("indicator", "schedule"):
            connection.execute(
                "INSERT INTO alerts (id,indicator_id,schedule_id,fired_at,title,summary,"
                "count,threshold,event_ids,countries,acknowledged_at,acknowledged_by,"
                "created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    uuid4().hex,
                    uuid4().hex if origin == "indicator" else None,
                    uuid4().hex if origin == "schedule" else None,
                    "2026-09-07 12:00:00",
                    origin,
                    "Preserve acknowledged public-source alert",
                    1,
                    1,
                    "[]",
                    "[]",
                    "2026-09-07 12:01:00",
                    owner,
                    owner,
                ),
            )
    return config, database, owner


def test_upgrade_preserves_old_origins_acknowledgements_and_matches_current_metadata(tmp_path):
    config, database, _ = prepared(tmp_path)
    with closing(sqlite3.connect(database)) as connection:
        alerts = connection.execute(
            "SELECT id,indicator_id,schedule_id,acknowledged_at,"
            "acknowledged_by,summary FROM alerts ORDER BY id"
        ).fetchall()
        users = connection.execute("SELECT * FROM users").fetchall()
    command.upgrade(config, "0030")
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
    command.downgrade(config, "0029")
    command.upgrade(config, "0030")
    with closing(sqlite3.connect(database)) as connection:
        assert (
            connection.execute(
                "SELECT id,indicator_id,schedule_id,acknowledged_at,"
                "acknowledged_by,summary FROM alerts ORDER BY id"
            ).fetchall()
            == alerts
        )
        assert connection.execute("SELECT * FROM users").fetchall() == users
        assert connection.execute(
            "SELECT annotation_monitor_id,annotation_transition_id FROM alerts"
        ).fetchall() == [(None, None), (None, None)]


@pytest.mark.parametrize("retained", [*sorted(TABLES), "damaged_alert"])
def test_retained_or_damaged_history_refuses_downgrade_before_any_ddl(tmp_path, retained):
    config, database, _ = prepared(tmp_path)
    command.upgrade(config, "0030")
    if retained == "damaged_alert":
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute(
                "UPDATE alerts SET annotation_transition_id=? "
                "WHERE id=(SELECT id FROM alerts LIMIT 1)",
                (uuid4().hex,),
            )
    else:
        engine = sa.create_engine(f"sqlite:///{database}")
        try:
            with engine.begin() as connection:
                table = sa.Table(retained, sa.MetaData(), autoload_with=connection)
                values = {}
                for column in table.columns:
                    if column.nullable:
                        values[column.name] = None
                    elif isinstance(column.type, sa.Integer):
                        values[column.name] = 1
                    elif isinstance(column.type, sa.Boolean):
                        values[column.name] = False
                    elif isinstance(column.type, sa.DateTime):
                        values[column.name] = datetime(2026, 9, 7, tzinfo=UTC)
                    elif isinstance(column.type, sa.JSON):
                        values[column.name] = []
                    else:
                        values[column.name] = "retained"
                connection.execute(table.insert().values(**values))
        finally:
            engine.dispose()
    with closing(sqlite3.connect(database)) as connection:
        before = tuple(connection.iterdump())
    with pytest.raises(RuntimeError, match="Refusing downgrade"):
        command.downgrade(config, "0029")
    with closing(sqlite3.connect(database)) as connection:
        assert tuple(connection.iterdump()) == before
