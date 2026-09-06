"""Upgrade existing accounts without losing credentials or access-revocation state."""

import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config


def test_security_version_migration_preserves_existing_account(tmp_path: Path) -> None:
    database = tmp_path / "existing-account.db"
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    # Explicit URL prevents fallback to operator settings or a real .env file.
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0011")
    identity = uuid4().hex
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO users (id,email,display_name,role,is_active,password_hash,"
            "failed_login_count,created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                identity,
                "existing@example.com",
                "Existing",
                "admin",
                1,
                "fixture-credential-hash",
                0,
                "2026-09-01 12:00:00",
            ),
        )
    command.upgrade(config, "0012")
    with closing(sqlite3.connect(database)) as connection, connection:
        assert connection.execute(
            "SELECT id,password_hash,security_version FROM users"
        ).fetchone() == (identity, "fixture-credential-hash", 0)
        connection.execute("INSERT INTO administration_lock (id) VALUES (1)")
    command.downgrade(config, "0011")
    with closing(sqlite3.connect(database)) as connection, connection:
        assert connection.execute("SELECT id,password_hash FROM users").fetchone() == (
            identity,
            "fixture-credential-hash",
        )
