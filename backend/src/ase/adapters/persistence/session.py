"""Engine and session factories that work for SQLite (dev, tests) and PostgreSQL (production)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from ase.adapters.persistence.session_changes import SIGNALS_KEY
from ase.application.ports.session import SessionSignals

SQLITE_PREFIX = "sqlite"


def is_sqlite(url: str) -> bool:
    return url.startswith(SQLITE_PREFIX)


def sqlite_path(url: str) -> Path | None:
    """Return the file path for a file-backed SQLite URL, or None for in-memory databases."""
    if not is_sqlite(url):
        return None
    _, _, tail = url.partition(":///")
    if not tail or tail == ":memory:":
        return None
    return Path(tail)


def ensure_sqlite_directory(url: str) -> None:
    path = sqlite_path(url)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)


def create_engine(url: str) -> AsyncEngine:
    kwargs: dict[str, Any] = {}
    if is_sqlite(url):
        kwargs["connect_args"] = {"check_same_thread": False}
        if sqlite_path(url) is None:
            # In-memory databases live on one connection; a static pool keeps them alive.
            kwargs["poolclass"] = StaticPool
    return create_async_engine(url, **kwargs)


def create_session_factory(
    engine: AsyncEngine, *, signals: SessionSignals | None = None
) -> async_sessionmaker[AsyncSession]:
    # Sessions share this info dict read-only; per-transaction marks live elsewhere.
    info = {SIGNALS_KEY: signals} if signals is not None else {}
    return async_sessionmaker(engine, expire_on_commit=False, info=info)
