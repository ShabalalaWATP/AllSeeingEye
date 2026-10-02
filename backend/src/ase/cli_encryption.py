"""Maintenance-only encryption rotation. Keys never travel through argv or output."""

from __future__ import annotations

import asyncio
import os
import stat
from pathlib import Path
from typing import Annotated

import typer


def _read_key(path: Path) -> str:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 4096:
        raise ValueError("Key files must be small regular files.")
    if os.name == "posix" and metadata.st_mode & 0o077:
        raise ValueError("Key files must be accessible only to their owner.")
    value = path.read_text(encoding="utf-8").strip()
    if len(value) < 32:
        raise ValueError("Invalid key file.")
    return value


async def _rotate(database_url: str, old: str, new: str) -> int:
    from ase.adapters.persistence.encryption_rotation import rotate_encryption_key  # noqa: PLC0415
    from ase.adapters.persistence.session import create_engine, sqlite_path  # noqa: PLC0415

    path = sqlite_path(database_url)
    if database_url.startswith("sqlite") and (path is None or not path.is_file()):
        raise ValueError("Rotation requires an existing persistent database.")
    engine = create_engine(database_url)
    try:
        return await rotate_encryption_key(engine, old, new)
    finally:
        await engine.dispose()


def rotate_key(
    old_key_file: Annotated[Path, typer.Option(help="Protected file containing the current key")],
    new_key_file: Annotated[
        Path, typer.Option(help="Protected file containing the replacement key")
    ],
    maintenance_confirmed: Annotated[
        bool, typer.Option(help="Confirm API/workers are stopped and a verified backup exists")
    ] = False,
) -> None:
    """Rotate the database selected by ASE_DATABASE_URL; update configuration afterwards."""
    from sqlalchemy.exc import SQLAlchemyError  # noqa: PLC0415

    from ase.adapters.security.cipher import CipherUnavailable  # noqa: PLC0415
    from ase.infrastructure.settings import Settings  # noqa: PLC0415

    if not maintenance_confirmed:
        typer.echo("Stop API/workers and verify a backup, then pass --maintenance-confirmed.")
        raise typer.Exit(code=1)
    try:
        old, new = _read_key(old_key_file), _read_key(new_key_file)
        count = asyncio.run(_rotate(Settings().database_url, old, new))
    except (OSError, ValueError, UnicodeError, CipherUnavailable, SQLAlchemyError):
        typer.echo(
            "Rotation failed or could not be confirmed. "
            "Keep services stopped and check a disposable copy."
        )
        raise typer.Exit(code=1) from None
    typer.echo(
        f"Rotated {count} encrypted values. Set the new configuration key before restarting."
    )
