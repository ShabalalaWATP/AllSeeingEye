"""Privacy decisions survive upgrades; downgrade cannot erase holds or tombstones."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert


def test_privacy_review_migration_and_preservation_guard(tmp_path):
    database = tmp_path / "privacy.sqlite"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0094")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        metadata = sa.MetaData()
        metadata.reflect(engine)
        with engine.begin() as connection:
            owner = _insert(
                connection, metadata.tables["users"], role="user", email="owner@example.com"
            )
        command.upgrade(config, "0095")
        command.downgrade(config, "0094")
        command.upgrade(config, "0095")
        metadata = sa.MetaData()
        metadata.reflect(engine)
        now = datetime(2026, 10, 16, tzinfo=UTC)
        with engine.begin() as connection:
            table = metadata.tables["private_data_reviews"]
            connection.execute(
                table.insert().values(
                    owner_id=owner,
                    revision=1,
                    decision="hold",
                    purpose="quarterly",
                    reviewed_by=owner,
                    reviewed_at=now,
                    next_review_at=now + timedelta(days=90),
                    erased_at=None,
                )
            )
        with pytest.raises(RuntimeError, match="privacy decisions"):
            command.downgrade(config, "0094")
        with engine.connect() as connection:
            assert connection.scalar(sa.select(table.c.decision)) == "hold"
    finally:
        engine.dispose()
        asyncio.set_event_loop(asyncio.new_event_loop())
