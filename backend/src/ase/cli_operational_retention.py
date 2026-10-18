"""Counts-only preview and explicit one-batch application of the same held policy."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Annotated

import typer

from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.infrastructure.settings import Settings


def operational_retention(
    apply: Annotated[bool, typer.Option("--apply", help="Apply one bounded batch")] = False,
) -> None:
    """Preview eligible counts. --apply explicitly deletes/minimises; holds always apply."""
    try:
        settings = Settings()
        counts = asyncio.run(_run(settings, dry_run=not apply))
    except Exception:
        typer.echo(
            "Operational maintenance failed. Check the selected database and policy "
            "before retrying.",
            err=True,
        )
        raise typer.Exit(code=1) from None
    typer.echo(
        json.dumps(
            {
                "dry_run": not apply,
                "paused": settings.operational_retention_paused,
                "held_categories": sorted(settings.operational_retention_held_categories),
                "counts": counts,
            }
        )
    )


async def _run(settings: Settings, *, dry_run: bool) -> dict[str, int]:
    # Migration CLI imports must stay independent of the application wiring.
    from ase.container.operational_retention import maintain_operations  # noqa: PLC0415

    engine = create_engine(settings.database_url)
    try:
        return await maintain_operations(
            create_session_factory(engine),
            datetime.now(UTC),
            settings.operational_retention_policy,
            dry_run=dry_run,
        )
    finally:
        await engine.dispose()
