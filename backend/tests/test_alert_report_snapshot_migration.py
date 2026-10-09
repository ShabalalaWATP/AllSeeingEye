"""Old pending intents fail explicitly; frozen evidence cannot be silently downgraded."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_snapshot_migration_preserves_alerts_without_replaying_legacy_work(tmp_path):
    path = tmp_path / "snapshot-migration.db"
    config = alembic_config(f"sqlite+aiosqlite:///{path.as_posix()}")
    engine = sa.create_engine(f"sqlite:///{path.as_posix()}")
    try:
        command.upgrade(config, "0090")
        with engine.begin() as connection:
            alerts = sa.Table("alerts", sa.MetaData(), autoload_with=connection)
            connection.execute(
                alerts.insert().values(
                    id=uuid4().hex,
                    indicator_id=uuid4().hex,
                    fired_at=datetime(2026, 9, 1, tzinfo=UTC),
                    title="Legacy pending alert",
                    summary="",
                    count=1,
                    threshold=1,
                    event_ids=[],
                    countries=[],
                    report_status="pending",
                    report_next_attempt_at=datetime(2026, 9, 1, tzinfo=UTC),
                )
            )
        command.upgrade(config, "0091")
        with engine.begin() as connection:
            alerts = sa.Table("alerts", sa.MetaData(), autoload_with=connection)
            row = connection.execute(sa.select(alerts)).one()
            assert row.report_status == "failed" and row.report_error == "evidence_unavailable"
            assert row.report_snapshot is None and row.report_next_attempt_at is None
            connection.execute(alerts.update().values(report_snapshot={"retained": True}))
        with pytest.raises(RuntimeError, match="frozen alert report evidence"):
            command.downgrade(config, "0090")
        with engine.begin() as connection:
            connection.execute(sa.text("UPDATE alerts SET report_snapshot = NULL"))
        command.downgrade(config, "0090")
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM alerts")) == 1
    finally:
        engine.dispose()
        asyncio.set_event_loop(asyncio.new_event_loop())
