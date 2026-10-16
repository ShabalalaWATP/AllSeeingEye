"""Explicit preview/apply operation, using the same policy as optional housekeeping."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Annotated

import typer

from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.domain.auth_retention import AuthRetentionPolicy
from ase.infrastructure.settings import Settings


def auth_retention(
    apply: Annotated[bool, typer.Option("--apply", help="Erase one bounded batch")] = False,
) -> None:
    """Preview bounded eligible counts; --apply explicitly erases them. Holds always apply."""
    try:
        settings = Settings()
        counts = asyncio.run(_run(settings, dry_run=not apply))
    except Exception:
        typer.echo(
            "Authentication maintenance failed. Check the selected database and policy "
            "before retrying.",
            err=True,
        )
        raise typer.Exit(code=1) from None
    typer.echo(
        json.dumps(
            {"dry_run": not apply, "paused": settings.auth_retention_paused, "counts": counts}
        )
    )


async def _run(settings: Settings, *, dry_run: bool) -> dict[str, int]:
    # Keep migration and other CLI startup paths independent of application wiring.
    from ase.container.auth_retention import maintain_authentication  # noqa: PLC0415

    engine = create_engine(settings.database_url)
    try:
        return await maintain_authentication(
            create_session_factory(engine),
            datetime.now(UTC),
            AuthRetentionPolicy(
                decision_days=settings.account_request_retention_days,
                paused=settings.auth_retention_paused,
            ),
            dry_run=dry_run,
        )
    finally:
        await engine.dispose()
