"""Explicit local dataset import, without database access or upstream requests."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, cast

import typer

from ase.adapters.research_records.designation_import import import_designation_csv


def import_designations(
    source: Annotated[Path, typer.Argument(help="Native UKSL or OFAC SDN CSV file")],
    cache_dir: Annotated[Path, typer.Option(help="Directory for a new immutable snapshot")],
    authority: Annotated[str, typer.Option(help="uksl or ofac_sdn")],
    version: Annotated[str, typer.Option(help="Unique snapshot version, never overwritten")],
    published_at: Annotated[str, typer.Option(help="ISO publisher date/time with UTC offset")],
    licence: Annotated[str, typer.Option(help="Applicable source licence or reuse restriction")],
) -> None:
    """Validate a selected CSV and create a bounded, immutable local snapshot."""
    if authority not in {"uksl", "ofac_sdn"}:
        raise typer.BadParameter("Choose uksl or ofac_sdn.")
    try:
        path = import_designation_csv(
            source,
            cache_dir,
            cast(Literal["uksl", "ofac_sdn"], authority),
            version,
            datetime.fromisoformat(published_at.replace("Z", "+00:00")),
            licence,
        )
    except (ValueError, OSError) as exc:
        typer.echo("Import failed: invalid input, unavailable destination or existing version.")
        raise typer.Exit(1) from exc
    typer.echo(f"Created {path}. Configure the matching ASE snapshot path to use it.")
    typer.echo("The source file is operator-supplied; its authenticity is not verified.")
