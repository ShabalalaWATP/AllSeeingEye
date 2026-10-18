"""Privileged local operator workflow, with password attribution and no public API."""

import asyncio
import json
from dataclasses import asdict
from typing import Any
from uuid import UUID

import typer

from ase.container import Container
from ase.domain.errors import AppError, InvalidCredentials
from ase.domain.private_removal import RemovalRequest, RemovalScope, ReviewDecision, ReviewPurpose
from ase.domain.users import Role
from ase.infrastructure.settings import Settings


def run_private_data(
    owner: UUID,
    operator: UUID,
    action: str,
    scope: str,
    target: UUID | None,
    fingerprint: str | None,
    decision: str | None,
    purpose: str,
    expected_revision: int,
    days: int,
) -> None:
    try:
        if action not in {"preview", "review", "apply"}:
            raise ValueError("Use preview, review or apply.")
        request = RemovalRequest(owner, RemovalScope(scope), target)
        review_decision = ReviewDecision(decision) if decision is not None else None
        review_purpose = ReviewPurpose(purpose)
        if action == "review" and (review_decision is None or scope != "account"):
            raise ValueError("A review requires account scope and an explicit decision.")
        if action == "apply" and fingerprint is None:
            raise ValueError("Apply requires the fingerprint from the reviewed preview.")
        if action != "review" and decision is not None:
            raise ValueError("Record necessity decisions with the review action.")
    except ValueError:
        typer.echo("Invalid private-data arguments. See private-data --help.", err=True)
        raise typer.Exit(code=2) from None
    password = typer.prompt("Current operator administrator password", hide_input=True)
    try:
        result = asyncio.run(
            _run(
                Settings(),
                operator,
                password,
                request,
                action,
                fingerprint,
                review_decision,
                review_purpose,
                expected_revision,
                days,
            )
        )
    except AppError as exc:
        typer.echo(exc.message, err=True)
        raise typer.Exit(code=1) from None
    except Exception:
        # Settings/database errors can contain URLs, credentials and SQL parameters.
        typer.echo(
            "Private-data outcome could not be confirmed; inspect the selected "
            "database and obtain a fresh preview before retrying.",
            err=True,
        )
        raise typer.Exit(code=1) from None
    typer.echo(json.dumps(result, default=str, sort_keys=True))


async def _run(
    settings: Settings,
    operator: UUID,
    password: str,
    request: RemovalRequest,
    action: str,
    fingerprint: str | None,
    decision: ReviewDecision | None,
    purpose: ReviewPurpose,
    expected_revision: int,
    days: int,
) -> dict[str, Any]:
    container = Container(settings)
    try:
        async with container.session_factory() as session:
            actor = await container.repositories(session).users.get_by_id(operator)
            if (
                actor is None
                or actor.role is not Role.ADMIN
                or not actor.can_log_in(container.clock.now())
                or not await container.hasher.verify(actor.password_hash or "", password)
            ):
                raise InvalidCredentials()
            service = container.private_removal(session)
            if action == "review":
                if decision is None:
                    raise ValueError("Missing review decision")
                review = await service.review(
                    actor, request.owner_id, decision, purpose, expected_revision, days=days
                )
                return {"action": action, "review": asdict(review)}
            if action == "apply":
                return {
                    "action": action,
                    "counts": await service.apply(actor, request, fingerprint or ""),
                }
            plan = await service.preview(actor, request)
            # Preview owns no durable mutation, including the no-op locks.
            return {"action": "preview", **asdict(plan)}
    finally:
        await container.dispose()
