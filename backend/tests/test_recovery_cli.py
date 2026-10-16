"""Trusted-host commands record minimised evidence without implying application or activation."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from ase.cli import app
from ase.cli_private_removal import _run
from ase.cli_recovery import open_journal
from ase.domain.errors import Conflict
from ase.domain.private_removal import RemovalRequest, RemovalScope, ReviewPurpose
from recovery_helpers import journal as journal  # noqa: PLC0414


def invoke(journal, command, *args):
    return CliRunner().invoke(
        app,
        [
            "recovery-record",
            command,
            "--journal",
            str(journal.path),
            "--key",
            str(journal.key),
            *args,
        ],
    )


def test_inspection_and_restriction_are_explicit_about_limits(journal):
    result = invoke(
        journal,
        "restriction",
        "--operator",
        str(uuid4()),
        "--owner",
        str(uuid4()),
        "--restriction",
        "email_opt_out",
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["database_or_delivery_changed"] is False
    inspected = invoke(journal, "journal", "inspect")
    assert inspected.exit_code == 0
    data = json.loads(inspected.output)
    assert data["activation_authorised"] is False
    assert data["events"][0]["status"] == "recorded"


@pytest.mark.parametrize(
    "kind,target",
    [
        ("subscription_opt_out", True),
        ("deactivate", False),
        ("push_revoke", False),
        ("feed_revoke", False),
        ("digest_opt_out", False),
    ],
)
def test_typed_restrictive_records(journal, kind, target):
    args = ["--operator", str(uuid4()), "--owner", str(uuid4()), "--restriction", kind]
    if target:
        args += ["--target", str(uuid4())]
    result = invoke(journal, "restriction", *args)
    assert result.exit_code == 0, result.output


def test_copy_reviews_require_explicit_selected_policy(journal):
    base = ["--operator", str(uuid4()), "--reference", str(uuid4()), "--category", "offsite"]
    invalid = invoke(journal, "copy-review", *base)
    assert invalid.exit_code == 2
    result = invoke(journal, "copy-review", *base, "--max-age-days", "120", "--keep-count", "30")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["copies_deleted"] is False
    record = journal.inspect()["events"][0]["action"]
    assert record["max_age_days"] == 120 and record["keep_count"] == 30


@pytest.mark.parametrize("args", [["--days", "0"], ["--days", "91"], ["--purpose", "unknown"]])
def test_invalid_review_metadata_never_appends(journal, args):
    result = invoke(
        journal,
        "restriction",
        "--operator",
        str(uuid4()),
        "--owner",
        str(uuid4()),
        "--restriction",
        "objection",
        *args,
    )
    assert result.exit_code in {1, 2}
    assert journal.inspect()["events"] == []


def test_initialisation_requires_new_paths_and_reports_legacy_gap(journal, tmp_path):
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    result = CliRunner().invoke(
        app,
        [
            "recovery-record",
            "journal",
            "initialise",
            "--journal",
            str(directory / "new"),
            "--key",
            str(directory / "key"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Empty history" in result.output
    assert invoke(journal, "journal", "initialise").exit_code == 1


def test_resolution_requires_evidence_and_current_head(journal):
    request = RemovalRequest(uuid4(), RemovalScope.ACCOUNT)
    event = journal.begin_removal(uuid4(), request, datetime.now(UTC))
    head = journal.inspect()["head_sha256"]
    result = invoke(
        journal,
        "journal",
        "resolve",
        "--event",
        str(event),
        "--operator",
        str(uuid4()),
        "--outcome",
        "applied",
        "--evidence",
        "a" * 64,
        "--head",
        head,
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["activation_authorised"] is False


@pytest.mark.parametrize(
    "action,extra",
    [
        ("inspect", ["--event", str(uuid4())]),
        ("initialise", ["--outcome", "applied"]),
        ("resolve", []),
        ("unknown", []),
    ],
)
def test_invalid_journal_action_arguments(journal, action, extra):
    result = invoke(journal, "journal", action, *extra)
    assert result.exit_code == 2


def test_io_failure_output_is_sanitised(journal, monkeypatch):
    def failing(*args):
        raise OSError("secret connection URL")

    monkeypatch.setattr("ase.cli_recovery.open_journal", failing)
    result = invoke(journal, "journal", "inspect")
    assert result.exit_code == 1
    assert "unconfirmed" in result.output and "secret" not in result.output


def test_known_repository_and_database_directories_are_rejected(journal, tmp_path):
    repo = Path(__file__).resolve().parents[2]
    with pytest.raises(Conflict, match="outside application"):
        open_journal(repo / "unsafe-recovery", journal.key)
    with pytest.raises(Conflict, match="outside application"):
        open_journal(
            journal.path, journal.key, f"sqlite+aiosqlite:///{journal.path.parent / 'data.db'}"
        )


async def test_private_writes_require_journal_even_when_called_directly(settings):
    with pytest.raises(ValueError, match="both recovery"):
        await _run(
            settings,
            uuid4(),
            "synthetic",
            RemovalRequest(uuid4(), RemovalScope.ACCOUNT),
            "review",
            None,
            None,
            ReviewPurpose.QUARTERLY,
            0,
            90,
        )


def test_private_command_passes_explicit_paths_and_never_echoes_password(journal, monkeypatch):
    run = AsyncMock(return_value={"action": "review"})
    monkeypatch.setattr("ase.cli_private_removal._run", run)
    result = CliRunner().invoke(
        app,
        [
            "private-data",
            "review",
            "--operator",
            str(uuid4()),
            "--owner",
            str(uuid4()),
            "--decision",
            "hold",
            "--journal",
            str(journal.path),
            "--journal-key",
            str(journal.key),
        ],
        input="synthetic-password\n",
    )
    assert result.exit_code == 0, result.output
    assert run.call_args.args[-2:] == (journal.path, journal.key)
    assert "synthetic-password" not in result.output


@pytest.mark.parametrize("extra", [[], ["--journal", "unused"], ["--journal-key", "unused"]])
def test_private_mutations_without_both_paths_stop_before_prompt(extra):
    result = CliRunner().invoke(
        app,
        [
            "private-data",
            "review",
            "--operator",
            str(uuid4()),
            "--owner",
            str(uuid4()),
            "--decision",
            "remove",
            *extra,
        ],
    )
    assert result.exit_code == 2 and "password" not in result.output.lower()


@pytest.mark.parametrize(
    "extra",
    [
        ["review", "--scope", "report", "--target", str(uuid4()), "--decision", "remove"],
        ["preview", "--decision", "hold"],
    ],
)
def test_private_invalid_scope_and_action_with_valid_journal(journal, extra):
    result = CliRunner().invoke(
        app,
        [
            "private-data",
            "--operator",
            str(uuid4()),
            "--owner",
            str(uuid4()),
            "--journal",
            str(journal.path),
            "--journal-key",
            str(journal.key),
            *extra,
        ],
    )
    assert result.exit_code == 2 and "password" not in result.output.lower()
