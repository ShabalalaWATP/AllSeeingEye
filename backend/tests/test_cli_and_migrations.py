"""The CLI and the migration path, both against temporary SQLite files."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ase.cli import app
from ase.infrastructure.migrations import upgrade_to_head

runner = CliRunner()
EXPECTED_TABLES = {"users", "account_requests", "refresh_tokens", "password_tokens", "audit_log"}


def test_migrations_create_the_schema(tmp_path: Path) -> None:
    db_file = tmp_path / "migrated.db"
    upgrade_to_head(f"sqlite+aiosqlite:///{db_file}")
    with closing(sqlite3.connect(db_file)) as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert names >= EXPECTED_TABLES
    assert "alembic_version" in names


def test_create_admin_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASE_ENV", "test")
    monkeypatch.setenv("ASE_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/cli.db")
    monkeypatch.setenv("ASE_JWT_SECRET", "s" * 40)
    monkeypatch.setenv("ASE_ADMIN_PASSWORD", "Orbital-Watchtower-2026")

    migrate = runner.invoke(app, ["migrate"])
    assert migrate.exit_code == 0, migrate.output
    assert "up to date" in migrate.output

    create = ["create-admin", "--email", "Boss@Example.com", "--display-name", "Boss"]
    created = runner.invoke(app, create)
    assert created.exit_code == 0, created.output
    assert "Created administrator boss@example.com" in created.output

    duplicate = runner.invoke(app, create)
    assert duplicate.exit_code == 1
    assert "already exists" in duplicate.output

    monkeypatch.setenv("ASE_ADMIN_PASSWORD", "password")
    weak = runner.invoke(app, ["create-admin", "--email", "w@example.com", "--display-name", "W"])
    assert weak.exit_code == 1
    assert "Password rejected" in weak.output

    with closing(sqlite3.connect(tmp_path / "cli.db")) as connection:
        rows = connection.execute("SELECT email, role, is_active FROM users").fetchall()
    assert rows == [("boss@example.com", "admin", 1)]


def test_export_openapi_command(tmp_path: Path) -> None:
    target = tmp_path / "out" / "openapi.json"
    result = runner.invoke(app, ["export-openapi", str(target)])
    assert result.exit_code == 0, result.output
    schema = json.loads(target.read_text(encoding="utf-8"))
    assert "/api/auth/login" in schema["paths"]
    assert "/api/admin/users/{user_id}" in schema["paths"]


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "create-admin" in result.output
