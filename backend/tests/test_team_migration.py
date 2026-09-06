"""Team migration preserves accounts without assigning them to invented shared groups."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_team_upgrade_and_downgrade_preserve_existing_account(tmp_path: Path) -> None:
    database = tmp_path / "team-migration.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0012")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO users (id,email,display_name,role,is_active,failed_login_count,"
            "created_at,security_version) VALUES (?,?,?,?,?,?,?,?)",
            ("1" * 32, "existing@example.com", "Existing", "user", 1, 0, "2026-09-06", 0),
        )
        connection.commit()
    command.upgrade(config, "0013")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT email FROM users").fetchall() == [
            ("existing@example.com",)
        ]
        assert connection.execute("SELECT * FROM teams").fetchall() == []
        assert connection.execute("SELECT * FROM team_memberships").fetchall() == []
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            "INSERT INTO teams VALUES (?,?,?,?,?,?)",
            ("2" * 32, "Desk", 1, "1" * 32, "2026-09-06", "2026-09-06"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO team_memberships VALUES (?,?,?,?)",
                ("2" * 32, "1" * 32, "admin", "2026-09-06"),
            )
        connection.commit()
    command.downgrade(config, "0012")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT email FROM users").fetchall() == [
            ("existing@example.com",)
        ]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        assert not {"teams", "team_memberships"} & tables
