"""Additive alert job links preserve history and never replay old alerts."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_alert_report_migration_preserves_old_alerts_and_refuses_lost_work(tmp_path):
    database = tmp_path / "alert-report-migration.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        command.upgrade(config, "0089")
        with engine.begin() as connection:
            alerts = sa.Table("alerts", sa.MetaData(), autoload_with=connection)
            connection.execute(
                alerts.insert().values(
                    id=uuid4().hex,
                    indicator_id=uuid4().hex,
                    fired_at=datetime(2026, 9, 1, tzinfo=UTC),
                    title="Historical alert",
                    summary="",
                    count=1,
                    threshold=1,
                    event_ids=[],
                    countries=[],
                )
            )
        command.upgrade(config, "0090")
        with engine.begin() as connection:
            alerts = sa.Table("alerts", sa.MetaData(), autoload_with=connection)
            row = connection.execute(sa.select(alerts)).one()
            assert row.title == "Historical alert" and row.report_status is None
            assert row.report_job_id is None and row.report_next_attempt_at is None
            inspector = sa.inspect(connection)
            foreign = inspector.get_foreign_keys("alerts")
            assert any(
                item["constrained_columns"] == ["report_job_id"]
                and item["options"].get("ondelete") == "SET NULL"
                for item in foreign
            )
            assert any(
                item["column_names"] == ["report_job_id"]
                for item in inspector.get_unique_constraints("alerts")
            )
            connection.execute(alerts.update().values(report_status="pending"))
        with pytest.raises(RuntimeError, match="alert report history"):
            command.downgrade(config, "0089")
        with engine.begin() as connection:
            connection.execute(alerts.update().values(report_status=None))
        command.downgrade(config, "0089")
        with engine.connect() as connection:
            assert "report_job_id" not in {
                item["name"] for item in sa.inspect(connection).get_columns("alerts")
            }
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM alerts")) == 1
    finally:
        engine.dispose()
        asyncio.set_event_loop(asyncio.new_event_loop())
