"""Existing token families receive one migration-time grace, without losing revocations."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_idle_migration_backfills_each_family_once_at_rollout_time(tmp_path):
    path = tmp_path / "idle-migration.sqlite"
    config = alembic_config(f"sqlite+aiosqlite:///{path.as_posix()}")
    engine = sa.create_engine(f"sqlite:///{path.as_posix()}")
    user, family = uuid4().hex, uuid4().hex
    historical = datetime(2026, 1, 1)
    try:
        command.upgrade(config, "0091")
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO users (id,email,display_name,role,is_active,"
                    "failed_login_count,created_at) "
                    "VALUES (:id,'legacy@example.com','Legacy','user',1,0,:at)"
                ),
                {"id": user, "at": historical},
            )
            for index in range(2):
                connection.execute(
                    sa.text(
                        "INSERT INTO refresh_tokens (id,user_id,token_hash,family_id,"
                        "issued_at,expires_at) "
                        "VALUES (:id,:user_id,:hash,:family,:at,:expires)"
                    ),
                    {
                        "id": uuid4().hex,
                        "user_id": user,
                        "hash": str(index) * 64,
                        "family": family,
                        "at": historical,
                        "expires": historical + timedelta(days=14),
                    },
                )
            connection.execute(
                sa.text(
                    "INSERT INTO refresh_family_revocations (family_id,revoked_at) "
                    "VALUES (:family,:at)"
                ),
                {"family": family, "at": historical},
            )
        before = datetime.now(UTC).replace(tzinfo=None)
        command.upgrade(config, "0092")
        after = datetime.now(UTC).replace(tzinfo=None)
        with engine.connect() as connection:
            activity = sa.Table("refresh_family_activity", sa.MetaData(), autoload_with=connection)
            row = connection.execute(sa.select(activity)).one()
            assert row.family_id == family and row.user_id == user
            assert before <= row.last_activity_at <= after
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM refresh_tokens")) == 2
            assert (
                connection.scalar(sa.text("SELECT COUNT(*) FROM refresh_family_revocations")) == 1
            )
        command.downgrade(config, "0091")
        with engine.connect() as connection:
            assert "refresh_family_activity" not in sa.inspect(connection).get_table_names()
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM refresh_tokens")) == 2
    finally:
        engine.dispose()
        asyncio.set_event_loop(asyncio.new_event_loop())
