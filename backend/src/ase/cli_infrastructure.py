"""Refresh packaged infrastructure snapshots. Network use is explicit, bounded and operator-run."""

from pathlib import Path
from typing import Annotated

import typer

from ase.adapters.geo.infrastructure_import import (
    DEFAULT_CONTACT,
    import_data_centres,
    import_ground_stations,
)

RESOURCES = Path(__file__).parent / "resources"
Contact = Annotated[
    str, typer.Option(help="Contact URL or address sent in the User-Agent (Wikimedia policy).")
]


def import_stations(
    destination: Annotated[Path, typer.Option(help="Ground station JSON to update.")] = RESOURCES
    / "ground_stations.json",
    contact: Contact = DEFAULT_CONTACT,
) -> None:
    """Merge Wikidata ground stations behind the curated list in the snapshot."""
    try:
        count = import_ground_stations(str(destination), contact=contact)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {count} ground stations to {destination}.")


def import_centres(
    destination: Annotated[Path, typer.Option(help="Data centre JSON to write.")] = RESOURCES
    / "data_centres.json",
    contact: Contact = DEFAULT_CONTACT,
) -> None:
    """Query OpenStreetMap for named data centres and write an attributed snapshot."""
    try:
        count = import_data_centres(str(destination), contact=contact)
    except Exception as exc:
        typer.echo(f"Import failed: {type(exc).__name__}. Check connectivity and retry.")
        raise typer.Exit(1) from exc
    typer.echo(f"Wrote {count} data centres to {destination}.")
    typer.echo("OpenStreetMap data is ODbL; keep the attribution in the snapshot.")
