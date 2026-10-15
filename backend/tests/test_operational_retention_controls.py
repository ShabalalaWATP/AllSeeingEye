"""Disabled defaults, strictly validated holds, safe CLI and independent worker ownership."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from structlog.testing import capture_logs
from typer.testing import CliRunner

from ase.adapters.persistence.models import AuditLogRow
from ase.app_lifecycle import lifespan
from ase.cli import app
from ase.cli_operational_retention import _run
from ase.container.operational_retention import run_operational_retention
from ase.domain.operational_retention import OperationalRetentionPolicy
from ase.infrastructure.settings import Settings
from helpers import USER_EMAIL, USER_PASSWORD, create_user
from operational_retention_helpers import audit, count, seed
from test_application_lifecycle import runtime as runtime  # noqa: PLC0414
from token_race_helpers import race_container as race_container  # noqa: PLC0414


@pytest.mark.parametrize("arguments,dry_run", [([], True), (["--apply"], False)])
def test_cli_requires_explicit_apply_and_prints_no_records(monkeypatch, arguments, dry_run):
    operation = AsyncMock(return_value={"audit": 4})
    monkeypatch.setattr("ase.cli_operational_retention._run", operation)
    result = CliRunner().invoke(app, ["operational-retention", *arguments])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "dry_run": dry_run,
        "paused": False,
        "held_categories": [],
        "counts": {"audit": 4},
    }
    assert operation.await_args.kwargs == {"dry_run": dry_run}


@pytest.mark.parametrize("target", ["Settings", "_run"])
def test_cli_failure_never_discloses_configuration_or_database_values(monkeypatch, target):
    failure = RuntimeError("synthetic-private-token")
    mock = Mock(side_effect=failure) if target == "Settings" else AsyncMock(side_effect=failure)
    monkeypatch.setattr("ase.cli_operational_retention." + target, mock)
    result = CliRunner().invoke(app, ["operational-retention", "--apply"])
    assert result.exit_code == 1 and "synthetic-private-token" not in result.output
    assert "Operational maintenance failed" in result.output


@pytest.mark.parametrize(
    "values",
    [
        {"audit_days": 29},
        {"usage_days": 3651},
        {"delivery_days": 0},
        {"batch_size": 0},
        {"batch_size": 101},
        {"held_categories": frozenset({"typo"})},
    ],
)
def test_policy_rejects_invalid_limits_and_hold_names(values):
    with pytest.raises(ValueError):
        OperationalRetentionPolicy(**values)


def test_settings_default_disabled_and_json_holds_validate(monkeypatch):
    settings = Settings(_env_file=None)
    assert not settings.operational_retention_enabled
    assert settings.operational_retention_policy == OperationalRetentionPolicy()
    monkeypatch.setenv("ASE_OPERATIONAL_RETENTION_HELD_CATEGORIES", '["audit","digest"]')
    assert Settings(_env_file=None).operational_retention_policy.held_categories == {
        "audit",
        "digest",
    }
    monkeypatch.setenv("ASE_OPERATIONAL_RETENTION_HELD_CATEGORIES", '["audit","typo"]')
    with pytest.raises(ValueError):
        Settings(_env_file=None)


async def test_worker_retries_without_sensitive_errors_and_stops_on_cancellation(
    monkeypatch, clock
):
    operation = AsyncMock(side_effect=[RuntimeError("private SQL"), {"audit": 1}, {"audit": 0}])
    sleeps = AsyncMock(side_effect=[None, None, asyncio.CancelledError()])
    monkeypatch.setattr("ase.container.operational_retention.maintain_operations", operation)
    monkeypatch.setattr("ase.container.operational_retention.asyncio.sleep", sleeps)
    with capture_logs() as logs, pytest.raises(asyncio.CancelledError):
        await run_operational_retention(object(), clock, OperationalRetentionPolicy())
    assert operation.await_count == 3
    assert operation.await_args.kwargs == {"dry_run": False}
    assert [entry["event"] for entry in logs] == [
        "operational_retention.failed",
        "operational_retention.completed",
    ]
    assert "private SQL" not in str(logs)


async def test_worker_starts_without_feeds_and_stops_before_disposal(runtime, monkeypatch):
    app_instance, container, tasks = runtime
    container.settings.feeds_enabled = False
    container.settings.operational_retention_enabled = True
    policy = OperationalRetentionPolicy(paused=True, held_categories=frozenset({"audit"}))
    container.settings.operational_retention_policy = policy
    started = asyncio.Event()

    async def worker(_sessions, _clock, selected):
        assert selected == policy
        tasks.append(asyncio.current_task())
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("ase.app_lifecycle.run_operational_retention", worker)
    async with lifespan(app_instance):
        await asyncio.wait_for(started.wait(), 10)
    assert all(task.done() for task in tasks)
    container.scheduler.start.assert_not_awaited()
    container.dispose.assert_awaited_once()


@pytest.mark.parametrize("dry_run,paused", [(True, False), (False, False), (False, True)])
async def test_cli_uses_selected_database_and_policy(race_container, dry_run, paused):
    container = race_container
    await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    await seed(container, audit(datetime.now(UTC) - timedelta(days=366)))
    settings = container.settings.model_copy(update={"operational_retention_paused": paused})
    assert (await _run(settings, dry_run=dry_run)).get("audit", 0) == (not paused)
    assert await count(container, AuditLogRow) == (dry_run or paused)


async def test_cli_disposes_after_transaction_failure(settings, monkeypatch):
    engine = Mock(dispose=AsyncMock())
    monkeypatch.setattr("ase.cli_operational_retention.create_engine", Mock(return_value=engine))
    monkeypatch.setattr("ase.cli_operational_retention.create_session_factory", Mock())
    monkeypatch.setattr(
        "ase.container.operational_retention.maintain_operations",
        AsyncMock(side_effect=RuntimeError()),
    )
    with pytest.raises(RuntimeError):
        await _run(settings, dry_run=False)
    engine.dispose.assert_awaited_once()
