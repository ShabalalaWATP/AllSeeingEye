"""Refresh the packaged Ukraine snapshots. Network use is explicit, bounded and operator-run."""

from pathlib import Path
from typing import Annotated

import typer

from ase.adapters.geo.bounded_download import DEFAULT_CONTACT
from ase.adapters.geo.ukraine_casualties_import import import_ukraine_casualties
from ase.adapters.geo.ukraine_control_import import import_ukraine_control
from ase.adapters.geo.ukraine_losses_import import import_ukraine_losses
from ase.adapters.geo.ukraine_oblasts_import import import_ukraine_oblasts
from ase.adapters.geo.ukraine_reference_import import import_ukraine_reference

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


def import_reference(
    destination: Annotated[
        Path, typer.Option(help="Reference catalogue JSON to write.")
    ] = RESOURCES / "ukraine_reference.json",
    contact: Contact = DEFAULT_CONTACT,
    reuse: Annotated[
        bool, typer.Option(help="Keep entries already resolved with a cached image.")
    ] = True,
) -> None:
    """Resolve the equipment, forces and timeline seeds through Wikidata and cache images."""
    try:
        count = import_ukraine_reference(str(destination), contact=contact, reuse=reuse)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {count} reference entries to {destination}.")
    typer.echo("Review image licences and credits before committing the catalogue.")


def import_losses(
    destination: Annotated[Path, typer.Option(help="Confirmed losses JSON to write.")] = RESOURCES
    / "ukraine_losses.json",
    contact: Contact = DEFAULT_CONTACT,
) -> None:
    """Fetch the newest Oryx daily file and a month of totals from the mirror."""
    try:
        count = import_ukraine_losses(str(destination), contact=contact)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {count} confirmed loss rows to {destination}.")


def import_casualties(
    destination: Annotated[Path, typer.Option(help="Civilian harm JSON to write.")] = RESOURCES
    / "ukraine_casualties.json",
    contact: Contact = DEFAULT_CONTACT,
) -> None:
    """Read the HRMMU monthly civilian harm pages and the curated casualty references."""
    try:
        count = import_ukraine_casualties(str(destination), contact=contact)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {count} civilian harm months to {destination}.")
