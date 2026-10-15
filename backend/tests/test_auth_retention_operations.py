"""Preview/apply controls, hold policy, independent worker and safe failure handling."""

import asyncio
import json
import os
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest
from structlog.testing import capture_logs
from typer.testing import CliRunner

from ase.cli import app
from ase.container.auth_retention import run_auth_retention
from ase.domain.auth_retention import AuthRetentionPolicy
from ase.infrastructure.settings import Settings


@pytest.mark.parametrize("arguments,dry_run", [([], True), (["--apply"], False)])
def test_cli_requires_explicit_apply_and_only_prints_counts(monkeypatch, arguments, dry_run):
    operation = AsyncMock(return_value={"password_links": 4})
    monkeypatch.setattr("ase.cli_auth_retention._run", operation)
    result = CliRunner().invoke(app, ["auth-retention", *arguments])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "dry_run": dry_run,
        "paused": False,
        "counts": {"password_links": 4},
    }
    assert operation.await_args.kwargs == {"dry_run": dry_run}


def test_cli_failure_does_not_disclose_database_details(monkeypatch):
    monkeypatch.setattr(
        "ase.cli_auth_retention._run", AsyncMock(side_effect=RuntimeError("private-dsn-token"))
    )
    result = CliRunner().invoke(app, ["auth-retention", "--apply"])
    assert result.exit_code == 1
    assert "private-dsn-token" not in result.output
    assert "Check the selected database and policy" in result.output


def test_invalid_settings_never_escape_as_a_secret_bearing_traceback(tmp_path):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("ASE_")}
    environment.update(ASE_ENV="test", ASE_SMTP_PASSWORD="synthetic-private-smtp")
    result = subprocess.run(
        [sys.executable, "-c", "from ase.cli import app; app()", "auth-retention"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 1
    assert "synthetic-private-smtp" not in result.stdout + result.stderr
    assert "Authentication maintenance failed" in result.stderr


@pytest.mark.parametrize(
    "values",
    [{"batch_size": 0}, {"batch_size": 101}, {"decision_days": 29}, {"decision_days": 3651}],
)
def test_policy_rejects_unbounded_or_invalid_windows(values):
    with pytest.raises(ValueError):
        AuthRetentionPolicy(**values)


def test_automatic_erasure_is_off_by_default():
    settings = Settings(_env_file=None)
    assert not settings.auth_retention_enabled
    assert not settings.auth_retention_paused
    assert settings.account_request_retention_days == 90


async def test_worker_retries_sanitised_failure_and_propagates_cancellation(monkeypatch, clock):
    operation = AsyncMock(side_effect=[RuntimeError("secret SQL"), {"password_links": 1}])
    sleeps = AsyncMock(side_effect=[None, asyncio.CancelledError()])
    monkeypatch.setattr("ase.container.auth_retention.maintain_authentication", operation)
    monkeypatch.setattr("ase.container.auth_retention.asyncio.sleep", sleeps)
    with capture_logs() as logs, pytest.raises(asyncio.CancelledError):
        await run_auth_retention(object(), clock, AuthRetentionPolicy())
    assert operation.await_count == 2
    assert operation.await_args.kwargs == {"dry_run": False}
    assert sleeps.await_args.args == (60,)
    assert [entry["event"] for entry in logs] == [
        "auth_retention.failed",
        "auth_retention.completed",
    ]
    assert "secret SQL" not in str(logs)
