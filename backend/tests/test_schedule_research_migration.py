"""Synthetic legacy schedules retain their meaning across the research migration."""

from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_research_schedule_migration_preserves_legacy_and_downgrades(tmp_path: Path) -> None:
    database = tmp_path / "schedule-research.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0014")
    engine = sa.create_engine(f"sqlite:///{database}")
    try:
        metadata = sa.MetaData()
        metadata.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(
                connection, metadata.tables["users"], email="owner@example.com", role="user"
            )
            schedule_id = _insert(
                connection, metadata.tables["schedules"], created_by=owner, name="Legacy daily"
            )
        command.upgrade(config, "0015")
        current = sa.Table("schedules", sa.MetaData(), autoload_with=engine)
        with engine.begin() as connection:
            row = connection.execute(sa.select(current)).mappings().one()
            assert row["id"] == schedule_id and row["name"] == "Legacy daily"
            assert row["question"] is None and row["research_options"] is None
            connection.execute(
                current.update().values(
                    question="Saved?", research_options={"mode": "quick", "languages": ["en"]}
                )
            )
        command.downgrade(config, "0014")
        reverted = sa.Table("schedules", sa.MetaData(), autoload_with=engine)
        assert "question" not in reverted.c and "research_options" not in reverted.c
        with engine.connect() as connection:
            row = connection.execute(sa.select(reverted)).mappings().one()
            assert row["id"] == schedule_id and row["name"] == "Legacy daily"
    finally:
        engine.dispose()


def test_change_migration_preserves_orphan_alert_and_refuses_lossy_downgrade(
    tmp_path: Path,
) -> None:
    database = tmp_path / "schedule-changes.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0015")
    engine = sa.create_engine(f"sqlite:///{database}")
    try:
        metadata = sa.MetaData()
        metadata.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(
                connection, metadata.tables["users"], email="owner@example.com", role="user"
            )
            schedule_id = _insert(connection, metadata.tables["schedules"], created_by=owner)
            orphan_id = _insert(
                connection, metadata.tables["alerts"], indicator_id=uuid4().hex, created_by=None
            )
        command.upgrade(config, "0016")
        alerts = sa.Table("alerts", sa.MetaData(), autoload_with=engine)
        schedules = sa.Table("schedules", sa.MetaData(), autoload_with=engine)
        with engine.begin() as connection:
            orphan = connection.execute(sa.select(alerts)).mappings().one()
            assert (
                orphan["id"] == orphan_id
                and orphan["created_by"] is None
                and orphan["schedule_id"] is None
            )
            assert connection.execute(sa.select(schedules.c.notify_on_change)).scalar_one() is False
            generated = _insert(
                connection, alerts, indicator_id=None, schedule_id=schedule_id, created_by=owner
            )
        with pytest.raises(RuntimeError, match="schedule-origin alerts"):
            command.downgrade(config, "0015")
        with engine.begin() as connection:
            assert len(list(connection.execute(sa.select(alerts)))) == 2
            # Remove only this test's synthetic alert to exercise the reversible legacy path.
            connection.execute(alerts.delete().where(alerts.c.id == generated))
        command.downgrade(config, "0015")
        reverted = sa.Table("alerts", sa.MetaData(), autoload_with=engine)
        assert "schedule_id" not in reverted.c
        with engine.connect() as connection:
            assert connection.execute(sa.select(reverted.c.id)).scalar_one() == orphan_id
    finally:
        engine.dispose()
