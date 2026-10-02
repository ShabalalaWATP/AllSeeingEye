"""Explicit local dataset import, without database access or upstream requests."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, cast

import typer


def import_designations(
    source: Annotated[Path, typer.Argument(help="Native UKSL/OFAC CSV or UN/EU XML file")],
    cache_dir: Annotated[Path, typer.Option(help="Directory for a new immutable snapshot")],
    authority: Annotated[str, typer.Option(help="uksl, ofac_sdn, un_sc or eu_fsf")],
    version: Annotated[str, typer.Option(help="Unique snapshot version, never overwritten")],
    published_at: Annotated[str, typer.Option(help="ISO publisher date/time with UTC offset")],
    licence: Annotated[str, typer.Option(help="Applicable source licence or reuse restriction")],
) -> None:
    """Validate a selected native list and create a bounded, immutable local snapshot."""
    # Dataset adapters must not load on the migration-only command path.
    from ase.adapters.research_records.designation_import import (  # noqa: PLC0415
        import_designation_csv,
    )
    from ase.adapters.research_records.designation_snapshot import (  # noqa: PLC0415
        SOURCE_URLS,
        Authority,
    )

    if authority not in SOURCE_URLS:
        raise typer.BadParameter("Choose uksl, ofac_sdn, un_sc or eu_fsf.")
    try:
        path = import_designation_csv(
            source,
            cache_dir,
            cast(Authority, authority),
            version,
            datetime.fromisoformat(published_at.replace("Z", "+00:00")),
            licence,
        )
    except (ValueError, OSError) as exc:
        typer.echo("Import failed: invalid input, unavailable destination or existing version.")
        raise typer.Exit(1) from exc
    typer.echo(f"Created {path}. Configure the matching ASE snapshot path to use it.")
    typer.echo("The source file is operator-supplied; its authenticity is not verified.")
