"""Upgrade marks incomplete legacy history; downgrade cannot discard consumption."""

import asyncio
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_consumption_migration_preserves_alerts_and_marks_only_matching_scope(tmp_path):
    database = tmp_path / "warning-consumption.sqlite"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0093")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    old = datetime(2026, 10, 1, tzinfo=UTC)
    try:
        metadata = sa.MetaData()
        metadata.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(connection, metadata.tables["users"], role="user")
            other = _insert(connection, metadata.tables["users"], role="user")
            rule = _insert(
                connection, metadata.tables["indicators"], created_by=owner, team_id=None
            )
            unused = _insert(
                connection, metadata.tables["indicators"], created_by=owner, team_id=None
            )
            for owner_id, fired in ((owner, old), (other, datetime(2026, 10, 2, tzinfo=UTC))):
                _insert(
                    connection,
                    metadata.tables["alerts"],
                    indicator_id=rule,
                    created_by=owner_id,
                    team_id=None,
                    fired_at=fired,
                    schedule_id=None,
                    annotation_monitor_id=None,
                    annotation_transition_id=None,
                )
        command.upgrade(config, "0094")
        with engine.connect() as connection:
            rows = connection.execute(sa.text("SELECT * FROM warning_consumption")).mappings().all()
            assert len(rows) == 1 and rows[0]["indicator_id"] == rule
            assert rows[0]["indicator_id"] != unused
            assert rows[0]["data"] == b"ASEC\x01" and rows[0]["count"] == 0
            assert str(rows[0]["legacy_before"]).startswith("2026-10-01")
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM alerts")) == 2
        with pytest.raises(RuntimeError, match="consumed warning evidence"):
            command.downgrade(config, "0093")
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM warning_consumption"))
        command.downgrade(config, "0093")
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM alerts")) == 2
            assert "warning_consumption" not in sa.inspect(connection).get_table_names()
    finally:
        engine.dispose()
        asyncio.set_event_loop(asyncio.new_event_loop())
