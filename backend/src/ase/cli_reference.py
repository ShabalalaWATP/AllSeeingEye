"""Refresh the packaged reference notes from Wikidata. Network use is explicit and bounded."""

from pathlib import Path
from typing import Annotated

import typer

from ase.adapters.reference_import import DEFAULT_CONTACT, import_reference


def import_reference_notes(
    destination: Annotated[
        Path, typer.Option(help="Reference JSON to write; defaults to the packaged resource.")
    ] = Path(__file__).parent / "resources" / "reference_entities.json",
    contact: Annotated[
        str,
        typer.Option(help="Contact URL or address sent in the User-Agent (Wikimedia policy)."),
    ] = DEFAULT_CONTACT,
) -> None:
    """Import ships with an MMSI and aircraft with a registration that have an article."""
    try:
        counts = import_reference(str(destination), contact=contact)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(
        f"Wrote {counts['vessel']} vessels, {counts['aircraft']} aircraft and "
        f"{counts['aircraft_type']} aircraft types to {destination}."
    )
