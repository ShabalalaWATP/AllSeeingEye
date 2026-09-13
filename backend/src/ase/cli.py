"""Operational commands: create the first admin, export the OpenAPI schema, run migrations."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer

from ase.adapters.persistence.session import ensure_sqlite_directory
from ase.cli_aiddata import import_aiddata
from ase.cli_designations import import_designations
from ase.cli_infrastructure import (
    import_centres,
    import_energy,
    import_notes,
    import_semiconductor,
    import_stations,
)
from ase.cli_public_figures import import_figures
from ase.cli_reference import import_reference_notes
from ase.cli_ukraine import import_control, import_oblasts, import_reference
from ase.container import Container
from ase.domain.errors import AppError, InvalidCredentials, WeakPassword
from ase.domain.password_policy import validate_password
from ase.domain.users import Role, User, normalise_email
from ase.infrastructure.migrations import upgrade_to_head
from ase.infrastructure.settings import Environment, Settings
from ase.main import create_app

app = typer.Typer(no_args_is_help=True, add_completion=False, help="The All Seeing Eye")
app.command("import-designations")(import_designations)
app.command("import-aiddata")(import_aiddata)
app.command("import-public-figures")(import_figures)
app.command("import-ground-stations")(import_stations)
app.command("import-data-centres")(import_centres)
app.command("import-energy-sites")(import_energy)
app.command("import-semiconductor-sites")(import_semiconductor)
app.command("import-infrastructure-notes")(import_notes)
app.command("import-reference")(import_reference_notes)
app.command("import-ukraine-control")(import_control)
app.command("import-ukraine-oblasts")(import_oblasts)
app.command("import-ukraine-reference")(import_reference)


@app.command("recover-admin-mfa")
def recover_admin_mfa(
    email: Annotated[str, typer.Option(help="Email of the administrator needing MFA recovery")],
) -> None:
    """Clear all admin factors locally, revoke sessions and require fresh MFA enrolment."""
    password = typer.prompt("Current administrator password", hide_input=True)
    typer.confirm("Remove all MFA methods and revoke this administrator's sessions?", abort=True)
    try:
        asyncio.run(_recover_admin_mfa(Settings(), normalise_email(email), password))
    except AppError as exc:
        typer.echo(exc.message)
        raise typer.Exit(code=1) from exc
    typer.echo("MFA removed. Sign in and enrol a new MFA method before accessing the app.")


async def _recover_admin_mfa(settings: Settings, email: str, password: str) -> None:
    container = Container(settings)
    try:
        async with container.session_factory() as session:
            user = await container.repositories(session).users.get_by_email(email)
            if user is None:
                raise InvalidCredentials()
            await container.mfa_management(session).recover_local(user, password)
    finally:
        await container.dispose()


@app.command("recover-admin-totp")
def recover_admin_totp(
    email: Annotated[
        str, typer.Option(help="Email of the administrator who lost their authenticator")
    ],
) -> None:
    """Remove local admin TOTP after password verification and revoke refresh sessions."""
    password = typer.prompt("Current administrator password", hide_input=True)
    typer.confirm("Remove this administrator's TOTP and revoke their refresh sessions?", abort=True)
    try:
        asyncio.run(_recover_admin_totp(Settings(), normalise_email(email), password))
    except AppError as exc:
        typer.echo(exc.message)
        raise typer.Exit(code=1) from exc
    typer.echo("TOTP removed. Sign in and enrol a new authenticator.")


async def _recover_admin_totp(settings: Settings, email: str, password: str) -> None:
    container = Container(settings)
    try:
        async with container.session_factory() as session:
            user = await container.repositories(session).users.get_by_email(email)
            if user is None:
                raise InvalidCredentials()
            await container.totp(session).recover_local(user, password)
    finally:
        await container.dispose()


@app.command("create-admin")
def create_admin(
    email: Annotated[str, typer.Option(help="Email address of the administrator")],
    display_name: Annotated[str, typer.Option(help="Name shown in the app")],
) -> None:
    """Create an active administrator. The password comes from ASE_ADMIN_PASSWORD or a prompt."""
    settings = Settings()
    password = (
        settings.admin_password.get_secret_value()
        if settings.admin_password
        else typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    )
    try:
        validate_password(password, email)
    except WeakPassword as exc:
        typer.echo(f"Password rejected: {(exc.fields or {}).get('new_password', exc.message)}")
        raise typer.Exit(code=1) from exc
    created = asyncio.run(_create_admin(settings, normalise_email(email), display_name, password))
    if not created:
        typer.echo("A user with that email already exists; nothing changed.")
        raise typer.Exit(code=1)
    typer.echo(f"Created administrator {normalise_email(email)}")


async def _create_admin(settings: Settings, email: str, display_name: str, password: str) -> bool:
    container = Container(settings)
    try:
        async with container.session_factory() as session:
            repos = container.repositories(session)
            if await repos.users.get_by_email(email) is not None:
                return False
            now = container.clock.now()
            await repos.users.add(
                User(
                    id=uuid4(),
                    email=email,
                    display_name=display_name.strip(),
                    role=Role.ADMIN,
                    is_active=True,
                    password_hash=container.hasher.hash(password),
                    failed_login_count=0,
                    last_failed_at=None,
                    locked_until=None,
                    created_at=now,
                    last_login_at=None,
                )
            )
            await repos.uow.commit()
            return True
    finally:
        await container.dispose()


@app.command("export-openapi")
def export_openapi(
    path: Annotated[Path, typer.Argument(help="Where to write the OpenAPI JSON")],
) -> None:
    """Write the OpenAPI schema so the frontend can generate its API types."""
    settings = Settings(_env_file=None, env=Environment.TEST, database_url="sqlite+aiosqlite://")
    schema = create_app(settings).openapi()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(schema, indent=2) + "\n").encode("utf-8"))
    typer.echo(f"Wrote {path}")


@app.command("migrate")
def migrate() -> None:
    """Apply database migrations up to the latest revision."""
    settings = Settings()
    ensure_sqlite_directory(settings.database_url)
    upgrade_to_head(settings.database_url)
    typer.echo("Database is up to date.")
