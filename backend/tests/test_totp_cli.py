"""Lost-device recovery is host-only, confirms intent and verifies the password."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ase.cli import app
from helpers import ADMIN_PASSWORD


def test_local_recovery_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "recovery.db"
    monkeypatch.setenv("ASE_ENV", "test")
    monkeypatch.setenv("ASE_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    monkeypatch.setenv("ASE_JWT_SECRET", "s" * 40)
    monkeypatch.setenv("ASE_ADMIN_PASSWORD", ADMIN_PASSWORD)
    runner = CliRunner()
    assert runner.invoke(app, ["migrate"]).exit_code == 0
    assert (
        runner.invoke(
            app, ["create-admin", "--email", "admin@example.com", "--display-name", "Admin"]
        ).exit_code
        == 0
    )
    command = ["recover-admin-totp", "--email", "admin@example.com"]
    cancelled = runner.invoke(app, command, input=f"{ADMIN_PASSWORD}\nn\n")
    assert cancelled.exit_code == 1
    wrong = runner.invoke(app, command, input="wrong\ny\n")
    assert wrong.exit_code == 1
    unknown = runner.invoke(
        app, ["recover-admin-totp", "--email", "none@example.com"], input=f"{ADMIN_PASSWORD}\ny\n"
    )
    assert unknown.exit_code == 1
    recovered = runner.invoke(app, command, input=f"{ADMIN_PASSWORD}\ny\n")
    assert recovered.exit_code == 0, recovered.output
    assert "TOTP removed" in recovered.output
    assert ADMIN_PASSWORD not in recovered.output
    with closing(sqlite3.connect(db)) as connection:
        actions = [row[0] for row in connection.execute("SELECT action FROM audit_log")]
    assert "totp_failed" in actions
    assert "totp_recovered" in actions


def test_local_mfa_recovery_removes_email_only_after_password_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "email-recovery.db"
    monkeypatch.setenv("ASE_ENV", "test")
    monkeypatch.setenv("ASE_DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    monkeypatch.setenv("ASE_JWT_SECRET", "s" * 40)
    monkeypatch.setenv("ASE_ADMIN_PASSWORD", ADMIN_PASSWORD)
    runner = CliRunner()
    assert runner.invoke(app, ["migrate"]).exit_code == 0
    assert (
        runner.invoke(
            app, ["create-admin", "--email", "admin@example.com", "--display-name", "Admin"]
        ).exit_code
        == 0
    )
    with closing(sqlite3.connect(db)) as connection:
        user_id, version = connection.execute("SELECT id, security_version FROM users").fetchone()
        connection.execute("INSERT INTO email_mfa (user_id, enabled) VALUES (?, 1)", (user_id,))
        connection.commit()
    command = ["recover-admin-mfa", "--email", "admin@example.com"]
    assert runner.invoke(app, command, input="wrong\ny\n").exit_code == 1
    with closing(sqlite3.connect(db)) as connection:
        assert connection.execute("SELECT enabled FROM email_mfa").fetchone() == (1,)
        assert connection.execute("SELECT security_version FROM users").fetchone() == (version,)
    recovered = runner.invoke(app, command, input=f"{ADMIN_PASSWORD}\ny\n")
    assert recovered.exit_code == 0, recovered.output
    assert "MFA removed" in recovered.output
    assert "enrol a new MFA method" in recovered.output
    assert ADMIN_PASSWORD not in recovered.output
    with closing(sqlite3.connect(db)) as connection:
        factor = connection.execute("SELECT enabled FROM email_mfa").fetchone()
        assert factor is None or factor == (0,)
        assert connection.execute("SELECT security_version FROM users").fetchone() == (version + 1,)
        actions = [row[0] for row in connection.execute("SELECT action FROM audit_log")]
    assert "mfa_recovered" in actions
