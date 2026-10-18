"""Trusted-host recovery evidence. These commands never reactivate a database."""

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import typer
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from ase.adapters.security.recovery_journal import FileRecoveryJournal
from ase.adapters.security.recovery_schema import CopyReview, Restriction
from ase.domain.errors import AppError, Conflict
from ase.domain.private_removal import ReviewPurpose


def open_journal(path: Path, key: Path, database_url: str | None = None) -> FileRecoveryJournal:
    excluded = []
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / ".git").exists():
            excluded.append(ancestor)
            break
    if database_url is not None:
        url = make_url(database_url)
        if url.get_backend_name() == "sqlite" and url.database not in {None, "", ":memory:"}:
            excluded.append(Path(url.database).resolve().parent)
    return FileRecoveryJournal(path, key, excluded=tuple(excluded))


def output(operation: Callable[[], object]) -> None:
    try:
        result = operation()
    except AppError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(code=1) from None
    except (ValidationError, ValueError):
        typer.echo("Invalid recovery record arguments. No activation is authorised.", err=True)
        raise typer.Exit(code=2) from None
    except Exception:
        typer.echo(
            "Recovery record outcome is unconfirmed. Inspect the protected files; "
            "do not initialise replacement history or activate a restored service.",
            err=True,
        )
        raise typer.Exit(code=1) from None
    typer.echo(json.dumps(result, default=str, sort_keys=True))


def journal_action(
    action: str,
    path: Path,
    key: Path,
    event: UUID | None,
    operator: UUID | None,
    outcome: str | None,
    evidence: str | None,
    head: str | None,
) -> object:
    journal = open_journal(path, key)
    if action == "initialise":
        if any(value is not None for value in (event, operator, outcome, evidence, head)):
            raise ValueError("Initialisation accepts only file paths")
        journal.initialise()
        return {
            "initialised": True,
            "coverage": "Empty history; investigate pre-existing decisions.",
        }
    if action == "inspect":
        if any(value is not None for value in (event, operator, outcome, evidence, head)):
            raise ValueError("Inspection accepts only file paths")
        return journal.inspect()
    if (
        action != "resolve"
        or event is None
        or operator is None
        or outcome not in {"applied", "not_applied"}
        or evidence is None
        or head is None
    ):
        raise ValueError(
            "Resolution requires an event, operator, evidence, outcome and current head"
        )
    journal.resolve(event, outcome == "applied", operator, evidence, head)
    return {"resolved_event": str(event), "activation_authorised": False}


def record_restriction(
    path: Path,
    key: Path,
    operator: UUID,
    owner: UUID,
    restriction: str,
    target: UUID | None,
    purpose: str,
    days: int,
) -> object:
    now, due = review_dates(days)
    action = Restriction.model_validate(
        {
            "owner": owner,
            "restriction": restriction,
            "target": target,
            "purpose": ReviewPurpose(purpose),
            "due": due,
        }
    )
    event = open_journal(path, key).record(operator, action, now)
    return {"event": str(event), "recorded_only": True, "database_or_delivery_changed": False}


def record_copy_review(
    path: Path,
    key: Path,
    operator: UUID,
    reference: UUID,
    category: str,
    purpose: str,
    days: int,
    max_age_days: int | None,
    keep_count: int | None,
    hold: bool,
) -> object:
    now, due = review_dates(days)
    action = CopyReview.model_validate(
        {
            "reference": reference,
            "category": category,
            "purpose": ReviewPurpose(purpose),
            "due": due,
            "max_age_days": max_age_days,
            "keep_count": keep_count,
            "hold": hold,
        }
    )
    event = open_journal(path, key).record(operator, action, now)
    return {"event": str(event), "recorded_only": True, "copies_deleted": False}


def review_dates(days: int) -> tuple[datetime, datetime]:
    if not 1 <= days <= 90:
        raise Conflict("Review intervals must be between one and ninety days.")
    now = datetime.now(UTC)
    return now, now + timedelta(days=days)
