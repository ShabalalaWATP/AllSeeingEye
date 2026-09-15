"""Add baseline acceptance without inventing decisions on old editions."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_existing_edition_backfills_false_and_accepted_history_blocks_downgrade(
    tmp_path: Path,
) -> None:
    database = tmp_path / "baseline-acceptance.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0037")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    metadata = sa.MetaData()
    metadata.reflect(engine)
    due = datetime(2026, 9, 7, 9, tzinfo=UTC)
    with engine.begin() as connection:
        owner = _insert(
            connection, metadata.tables["users"], email="accept@example.com", role="user"
        )
        schedule_id = _insert(
            connection,
            metadata.tables["schedules"],
            created_by=owner,
            name="Existing edition",
            template_id="intsum",
            next_run_at=due,
        )
        connection.execute(
            metadata.tables["subscription_revisions"]
            .insert()
            .values(
                subscription_id=schedule_id,
                revision=1,
                owner_id=owner,
                request_snapshot="{}",
                compatibility_fingerprint="a" * 64,
                recurrence_policy="local_iana_v1",
                collection_policy="rolling_snapshot_v1",
                enabled=True,
                created_at=due - timedelta(days=1),
            )
        )
        edition_id = _insert(
            connection,
            metadata.tables["subscription_editions"],
            subscription_id=schedule_id,
            trigger="scheduled",
            due_at_utc=due,
            frozen_revision=1,
            requested_start=due - timedelta(days=1),
            requested_end=due,
            effective_intervals=[],
            gaps=[],
            compatibility_fingerprint="a" * 64,
            workflow="pending",
            report_quality="absent",
            coverage="unknown",
            created_at=due - timedelta(days=1),
            updated_at=due - timedelta(days=1),
            revision=1,
        )
    command.upgrade(config, "0038")
    metadata.clear()
    metadata.reflect(engine)
    table = metadata.tables["subscription_editions"]
    with engine.connect() as connection:
        accepted = connection.scalar(
            sa.select(table.c.accepted_as_baseline).where(table.c.id == edition_id)
        )
    assert accepted is False
    with engine.begin() as connection:
        connection.execute(
            sa.update(table).where(table.c.id == edition_id).values(accepted_as_baseline=True)
        )
    with pytest.raises(RuntimeError, match="acceptance history"):
        command.downgrade(config, "0037")
    engine.dispose()
