"""Database fixtures for concurrent token tests, isolated from operator databases."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from ase.adapters.persistence.base import Base
from ase.application.dto import RequestContext
from ase.container import Container
from ase.infrastructure.settings import Settings
from helpers import FakeClock

CONTEXT = RequestContext(ip="race-test", user_agent="test")


@pytest.fixture
async def race_container(
    settings: Settings,
    clock: FakeClock,
    tmp_path: Path,
) -> AsyncIterator[Container]:
    # An explicit override must point only at an owned disposable test database.
    url = os.environ.get(
        "ASE_TOKEN_RACE_TEST_URL", f"sqlite+aiosqlite:///{tmp_path / 'token-races.db'}"
    )
    isolated = settings.model_copy(update={"database_url": url})
    container = Container(isolated, clock=clock)
    async with container.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield container
    finally:
        await container.dispose()
