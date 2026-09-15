"""Real multi-connection databases for race tests: file SQLite, or disposable PostgreSQL."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.session import create_engine


async def race_engine(tmp_path: Path, name: str) -> AsyncEngine:
    """Fresh schema on ASE_TOKEN_RACE_TEST_URL when set, otherwise a file-backed SQLite."""
    # An explicit override must point only at an owned disposable test database.
    url = os.environ.get("ASE_TOKEN_RACE_TEST_URL", f"sqlite+aiosqlite:///{tmp_path / name}")
    engine = create_engine(url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    return engine
