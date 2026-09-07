"""Async Alembic environment. The URL comes from the config, else from the app settings."""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from ase.adapters.persistence import (  # noqa: F401 (registers feature tables)
    claim_models,
    identity_models,
    llm_bindings,
    map_view_models,
    mfa_models,
    models,
    profile,
    recovery_models,
    report_search,
    source_control_models,
    teams,
    token_families,
    totp,
)
from ase.adapters.persistence.base import Base
from ase.infrastructure.settings import Settings

config = context.config
target_metadata = Base.metadata


def get_url() -> str:
    return config.get_main_option("sqlalchemy.url") or Settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
