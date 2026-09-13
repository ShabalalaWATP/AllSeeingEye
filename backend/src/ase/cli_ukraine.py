"""Refresh the packaged Ukraine snapshots. Network use is explicit, bounded and operator-run."""

from pathlib import Path
from typing import Annotated

import typer

from ase.adapters.geo.bounded_download import DEFAULT_CONTACT
from ase.adapters.geo.ukraine_control_import import import_ukraine_control
from ase.adapters.geo.ukraine_oblasts_import import import_ukraine_oblasts

RESOURCES = Path(__file__).parent / "resources"
Contact = Annotated[str, typer.Option(help="Contact URL or address sent in the User-Agent.")]


def import_control(
    destination: Annotated[Path, typer.Option(help="Control snapshot JSON to write.")] = RESOURCES
    / "ukraine_control.json",
    contact: Contact = DEFAULT_CONTACT,
) -> None:
    """Download VIINA's daily territorial control release and write the bounded snapshot."""
    try:
        count = import_ukraine_control(str(destination), contact=contact)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {count} frontline-zone settlements to {destination}.")


def import_oblasts(
    destination: Annotated[Path, typer.Option(help="Oblast outline JSON to write.")] = RESOURCES
    / "ukraine_oblasts.json",
    contact: Contact = DEFAULT_CONTACT,
) -> None:
    """Download geoBoundaries oblast outlines and write a simplified attributed file."""
    try:
        count = import_ukraine_oblasts(str(destination), contact=contact)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {count} oblast outlines to {destination}.")
