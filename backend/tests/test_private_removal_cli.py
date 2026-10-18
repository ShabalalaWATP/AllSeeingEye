"""Local operator authentication, default preview and sanitised command failures."""

import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from typer.testing import CliRunner

from ase.adapters.persistence.models import ReportRow
from ase.cli import app
from ase.cli_private_removal import _run
from ase.container import Container
from ase.domain.errors import InvalidCredentials
from ase.domain.private_removal import RemovalRequest, RemovalScope, ReviewDecision, ReviewPurpose
from ase.domain.users import Role
from helpers import ADMIN_PASSWORD, USER_PASSWORD, create_user
from private_removal_helpers import report
from token_race_helpers import race_container as race_container  # noqa: PLC0414


@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_real_database_cli_review_preview_apply(race_container, monkeypatch, cleanup_fails):
    container = race_container
    admin = await create_user(
        container, email="operator@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    user = await create_user(container, email="owner@example.com", password=USER_PASSWORD)
    target, _ = await report(container, user)
    account = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    review = await _run(
        container.settings,
        admin.id,
        ADMIN_PASSWORD,
        account,
        "review",
        None,
        ReviewDecision.REMOVE,
        ReviewPurpose.RIGHTS_REQUEST,
        0,
        90,
    )
    assert review["review"]["revision"] == 1
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    plan = await _run(
        container.settings,
        admin.id,
        ADMIN_PASSWORD,
        request,
        "preview",
        None,
        None,
        ReviewPurpose.QUARTERLY,
        0,
        90,
    )
    assert not plan["blockers"] and plan["counts"]["reports"] == 1
    async with container.session_factory() as session:
        assert await session.get(ReportRow, target.id) is not None
    if cleanup_fails:

        def failing_cleanup(settings):
            instance = Container(settings)
            dispose = instance.dispose

            async def fail_after_dispose():
                await dispose()
                raise RuntimeError("Synthetic cleanup failure after commit")

            instance.dispose = fail_after_dispose
            return instance

        monkeypatch.setattr("ase.cli_private_removal.Container", failing_cleanup)
    operation = _run(
        container.settings,
        admin.id,
        ADMIN_PASSWORD,
        request,
        "apply",
        plan["fingerprint"],
        None,
        ReviewPurpose.QUARTERLY,
        0,
        90,
    )
    if cleanup_fails:
        with pytest.raises(RuntimeError, match="after commit"):
            await operation
    else:
        assert (await operation)["counts"] == plan["counts"]
    async with container.session_factory() as session:
        assert await session.scalar(select(ReportRow)) is None


@pytest.mark.parametrize("kind", ["wrong_password", "ordinary_user", "missing", "inactive"])
async def test_cli_requires_current_active_admin_password(race_container, kind):
    container = race_container
    actor = await create_user(
        container,
        email="operator@example.com",
        password=ADMIN_PASSWORD,
        role=Role.USER if kind == "ordinary_user" else Role.ADMIN,
        is_active=kind != "inactive",
    )
    with pytest.raises(InvalidCredentials):
        await _run(
            container.settings,
            uuid4() if kind == "missing" else actor.id,
            "wrong" if kind == "wrong_password" else ADMIN_PASSWORD,
            RemovalRequest(actor.id, RemovalScope.ACCOUNT),
            "preview",
            None,
            None,
            ReviewPurpose.QUARTERLY,
            0,
            90,
        )


def args(*extra):
    return ["private-data", "--owner", str(uuid4()), "--operator", str(uuid4()), *extra]


def test_command_defaults_to_preview_and_keeps_password_hidden(monkeypatch):
    run = AsyncMock(return_value={"action": "preview", "counts": {}, "blockers": []})
    monkeypatch.setattr("ase.cli_private_removal._run", run)
    result = CliRunner().invoke(app, args(), input="synthetic-private-password\n")
    assert result.exit_code == 0, result.output
    assert "synthetic-private-password" not in result.output
    assert json.loads(result.output.splitlines()[-1])["action"] == "preview"
    assert run.call_args.args[4] == "preview"


@pytest.mark.parametrize(
    "extra",
    [
        ["invalid"],
        ["apply"],
        ["review"],
        ["--scope", "report"],
        ["--target", str(uuid4())],
        ["--decision", "remove"],
        ["--purpose", "invalid"],
        ["review", "--scope", "job", "--target", str(uuid4()), "--decision", "remove"],
    ],
)
def test_invalid_arguments_fail_before_password_prompt(extra):
    result = CliRunner().invoke(app, args(*extra))
    assert result.exit_code == 2
    assert "password" not in result.output.lower()


@pytest.mark.parametrize("failure", ["settings", "database", "credentials"])
def test_command_errors_never_echo_credentials_or_sql(monkeypatch, failure):
    private = "postgresql://private:secret@example.invalid/db SQL parameters"

    def invalid_settings():
        raise ValueError(private)

    if failure == "settings":
        monkeypatch.setattr("ase.cli_private_removal.Settings", invalid_settings)
    else:
        error = InvalidCredentials() if failure == "credentials" else RuntimeError(private)
        monkeypatch.setattr("ase.cli_private_removal._run", AsyncMock(side_effect=error))
    result = CliRunner().invoke(app, args(), input="synthetic-private-password\n")
    assert result.exit_code == 1
    assert "secret" not in result.output and "synthetic-private-password" not in result.output
    assert "Traceback" not in result.output
    if failure != "credentials":
        assert "outcome could not be confirmed" in result.output
