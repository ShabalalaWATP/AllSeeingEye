"""Additive local-time backfill against a disposable legacy SQLite database."""

from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_legacy_utc_schedule_keeps_exact_due_slot_and_hour(tmp_path: Path) -> None:
    database = tmp_path / "legacy-s04.db"
    sync_url = f"sqlite:///{database.as_posix()}"
    async_url = f"sqlite+aiosqlite:///{database.as_posix()}"
    config = alembic_config(async_url)
    command.upgrade(config, "0036")
    engine = sa.create_engine(sync_url)
    metadata = sa.MetaData()
    metadata.reflect(engine)
    due = datetime(2026, 10, 25, 1, tzinfo=UTC)
    with engine.begin() as connection:
        owner = _insert(connection, metadata.tables["users"], email="s04@example.com", role="user")
        schedule_id = _insert(
            connection,
            metadata.tables["schedules"],
            created_by=owner,
            name="Legacy UTC",
            template_id="intsum",
            cadence="daily",
            hour_utc=1,
            weekday=0,
            next_run_at=due,
        )
    command.upgrade(config, "0037")
    metadata.clear()
    metadata.reflect(engine)
    with engine.connect() as connection:
        row = (
            connection.execute(
                sa.select(metadata.tables["schedules"]).where(
                    metadata.tables["schedules"].c.id == schedule_id
                )
            )
            .mappings()
            .one()
        )
    assert row["hour_utc"] == row["local_hour"] == 1
    assert row["timezone"] == "UTC" and row["local_minute"] == 0
    assert row["collection_policy"] == "rolling_snapshot"
    assert row["next_run_at"] == due.replace(tzinfo=None)
    engine.dispose()
