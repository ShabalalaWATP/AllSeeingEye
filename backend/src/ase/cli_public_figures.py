"""Refresh the packaged office-holder roster from Wikidata. Network use is explicit and bounded."""

from pathlib import Path
from typing import Annotated

import typer

from ase.adapters.geo.public_figures_import import DEFAULT_CONTACT, import_public_figures


def import_figures(
    destination: Annotated[
        Path,
        typer.Option(help="Roster JSON to write; defaults to the packaged resource."),
    ] = Path(__file__).parent / "resources" / "public_figures.json",
    contact: Annotated[
        str,
        typer.Option(help="Contact URL or address sent in the User-Agent, per Wikimedia policy."),
    ] = DEFAULT_CONTACT,
) -> None:
    """Query Wikidata for current heads of state and government and organisation leaders."""
    try:
        count = import_public_figures(str(destination), contact=contact)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {count} figures to {destination}.")
    typer.echo("Review incumbents and portrait licences before committing the roster.")
