"""Only disposable SQLite files are used for MFA upgrade/downgrade checks."""

import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config


def prepare(tmp_path: Path) -> tuple[Config, Path, str]:
    database = tmp_path / "mfa-migration.db"
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0018")
    identity = uuid4().hex
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO users (id,email,display_name,role,is_active,password_hash,"
            "failed_login_count,created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                identity,
                "mfa@example.test",
                "MFA",
                "admin",
                1,
                "fixture-hash",
                0,
                "2026-09-01 12:00:00",
            ),
        )
        connection.execute(
            "INSERT INTO refresh_tokens (id,user_id,token_hash,family_id,issued_at,expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                uuid4().hex,
                identity,
                "a" * 64,
                uuid4().hex,
                "2026-09-01 12:00:00",
                "2026-09-10 12:00:00",
            ),
        )
    return config, database, identity


def test_upgrade_keeps_existing_sessions_unverified_and_empty_downgrade(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0019")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT mfa_verified FROM refresh_tokens").fetchone() == (0,)
        assert connection.execute("SELECT id,password_hash FROM users").fetchone() == (
            identity,
            "fixture-hash",
        )
    command.downgrade(config, "0018")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT count(*) FROM refresh_tokens").fetchone() == (1,)
        assert "mfa_verified" not in {
            row[1] for row in connection.execute("PRAGMA table_info(refresh_tokens)")
        }


def test_upgrade_preserves_existing_authenticator_and_replay_state(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO admin_totp (user_id,secret_encrypted,last_step) VALUES (?, ?, ?)",
            (identity, "synthetic-ciphertext", 123456),
        )
    command.upgrade(config, "0019")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT user_id,secret_encrypted,last_step FROM admin_totp"
        ).fetchone() == (identity, "synthetic-ciphertext", 123456)


@pytest.mark.parametrize("factor", ["email", "authenticator"])
def test_downgrade_refuses_configured_factor_before_any_ddl(tmp_path: Path, factor: str) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0019")
    with closing(sqlite3.connect(database)) as connection, connection:
        if factor == "email":
            connection.execute("INSERT INTO email_mfa (user_id,enabled) VALUES (?, 1)", (identity,))
        else:
            connection.execute(
                "INSERT INTO admin_totp (user_id,secret_encrypted) VALUES (?, ?)",
                (identity, "synthetic-ciphertext"),
            )
    with pytest.raises(RuntimeError, match="Cannot downgrade"):
        command.downgrade(config, "0018")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0019",)
        assert connection.execute("SELECT count(*) FROM mfa_challenges").fetchone() == (0,)
        assert connection.execute("SELECT mfa_verified FROM refresh_tokens").fetchone() == (0,)
