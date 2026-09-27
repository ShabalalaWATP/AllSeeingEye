"""Real multi-connection databases for race tests: file SQLite, or disposable PostgreSQL."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from ase.adapters.persistence.session import create_engine
from pytest_support import create_schema, disposable_database, skip_sqlite_fsync


async def race_engine(tmp_path: Path, name: str) -> AsyncEngine:
    """Fresh schema on ASE_TOKEN_RACE_TEST_URL when set, otherwise a file-backed SQLite."""
    # An explicit override must point only at an owned disposable test database.
    url = os.environ.get("ASE_TOKEN_RACE_TEST_URL", f"sqlite+aiosqlite:///{tmp_path / name}")
    engine = create_engine(url)
    skip_sqlite_fsync(engine)
    await create_schema(engine, fresh=disposable_database(url))
    return engine
