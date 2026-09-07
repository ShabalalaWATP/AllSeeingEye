"""Explicit native project import without modifying the operator application database."""

import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from ase.adapters.research_records.aiddata_catalogue import import_project_directory


def import_aiddata(
    source: Annotated[
        Path, typer.Argument(help="Directory containing native GeoGCDF project GeoJSON files")
    ],
    cache_dir: Annotated[
        Path, typer.Option(help="Destination for an immutable reference catalogue")
    ],
) -> None:
    """Build a bounded GeoGCDF v3.0.1 catalogue from selected local project files."""
    try:
        target = import_project_directory(source, cache_dir)
    except (ValueError, OSError, sqlite3.Error) as exc:
        typer.echo("Import failed: invalid input, unavailable destination or existing catalogue.")
        raise typer.Exit(1) from exc
    typer.echo(f"Created {target}")
    typer.echo(
        "Source authenticity is unverified. An imported subset is not full release coverage."
    )
    typer.echo("This command does not activate a source or modify the application database.")
