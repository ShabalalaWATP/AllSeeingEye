"""The archive column upgrades old rows and cannot discard live tombstones."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_0042_backfills_active_and_blocks_destructive_downgrade(tmp_path: Path) -> None:
    database = tmp_path / "subscription-archive-disposable.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0041")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        metadata = sa.MetaData()
        metadata.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(
                connection, metadata.tables["users"], email="archive@example.com", role="user"
            )
            schedule_id = _insert(
                connection,
                metadata.tables["schedules"],
                created_by=owner,
                name="Old subscription",
                template_id="intsum",
                next_run_at=datetime(2026, 9, 14, tzinfo=UTC),
                enabled=True,
            )
        command.upgrade(config, "0042")
        metadata.clear()
        metadata.reflect(engine)
        schedules = metadata.tables["schedules"]
        with engine.connect() as connection:
            row = connection.execute(
                sa.select(schedules.c.enabled, schedules.c.archived_at).where(
                    schedules.c.id == schedule_id
                )
            ).one()
            assert row == (True, None)
        with engine.begin() as connection:
            connection.execute(
                sa.update(schedules)
                .where(schedules.c.id == schedule_id)
                .values(enabled=False, archived_at=datetime(2026, 9, 14, tzinfo=UTC))
            )
        with pytest.raises(RuntimeError, match="tombstones"):
            command.downgrade(config, "0041")
        with engine.begin() as connection:
            connection.execute(
                sa.update(schedules).where(schedules.c.id == schedule_id).values(archived_at=None)
            )
        command.downgrade(config, "0041")
        assert "archived_at" not in {
            column["name"] for column in sa.inspect(engine).get_columns("schedules")
        }
    finally:
        engine.dispose()
