"""Additive SQLite upgrades and PostgreSQL DDL for dispositions and rule ratios."""

from io import StringIO
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_sqlite_upgrade_preserves_existing_alerts_and_downgrade_guards_feedback(tmp_path):
    database = tmp_path / "alert-feedback.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0066")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        meta = sa.MetaData()
        meta.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(connection, meta.tables["users"], email="feedback@example.test")
            rule = _insert(connection, meta.tables["indicators"], created_by=owner)
            _insert(
                connection,
                meta.tables["alerts"],
                indicator_id=rule,
                created_by=owner,
                schedule_id=None,
                annotation_monitor_id=None,
                annotation_transition_id=None,
            )
            before = dict(connection.execute(sa.select(meta.tables["alerts"])).mappings().one())
        command.upgrade(config, "0070")
        meta.clear()
        meta.reflect(engine)
        with engine.begin() as connection:
            after = dict(connection.execute(sa.select(meta.tables["alerts"])).mappings().one())
            assert all(after[key] == value for key, value in before.items())
            assert after["disposition"] is after["baseline_ratio"] is None
            connection.execute(
                meta.tables["alert_feedback_days"]
                .insert()
                .values(
                    indicator_id=uuid4().hex,
                    day=before["fired_at"],
                    disposition="useful",
                    count=1,
                )
            )
        command.downgrade(config, "0069")
        with pytest.raises(RuntimeError, match="retained alert feedback"):
            command.downgrade(config, "0066")
    finally:
        engine.dispose()


def test_postgresql_upgrade_ddl_is_renderable_without_a_live_database():
    config = alembic_config("postgresql+asyncpg://fixture:fixture@localhost/unused")
    output = StringIO()
    config.output_buffer = output
    # The parent data migration reads retained jobs; render only this batch's DDL.
    command.upgrade(config, "0068:0070", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE alert_feedback_days" in sql
    assert "ADD COLUMN baseline_ratio" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql
