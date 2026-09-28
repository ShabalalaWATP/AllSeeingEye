"""Cached administrator source switches reload after every committed change."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import event, insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.adapters.persistence.source_control_changes import source_control_version
from ase.adapters.persistence.source_control_models import SourceControlRow
from ase.adapters.persistence.source_controls import SqlSourceAdmission, SqlSourceControlRepository
from ase.container import Container
from ase.domain.users import User
from feeds_helpers import NOW, FakeConnector
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_events_api import app  # noqa: F401 (shared isolated connector fixture)

ACTOR = uuid4()


def count_control_reads(engine: AsyncEngine) -> list[str]:
    """Admission snapshot loads only; repository reads by primary key are not counted."""
    reads: list[str] = []

    def record(_conn, _cursor, statement, _params, _context, _many) -> None:
        if "WHERE source_controls.enabled IS" in statement:
            reads.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record)
    return reads


@pytest.fixture
async def database(tmp_path: Path) -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], list]]:
    engine = create_engine(f"sqlite+aiosqlite:///{(tmp_path / 'controls.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all, tables=[SourceControlRow.__table__])
    yield create_session_factory(engine), count_control_reads(engine)
    await engine.dispose()


async def switch(sessions, source_id: str, enabled: bool, *, commit: bool = True) -> None:
    async with sessions() as session:
        await SqlSourceControlRepository(session).set(source_id, enabled, NOW, ACTOR)
        if commit:
            await session.commit()


async def test_repeated_checks_share_one_read(database) -> None:
    sessions, reads = database
    gate = SqlSourceAdmission(sessions, ("environment_off",))
    for _ in range(3):
        assert await gate.enabled("feed")
    assert await gate.enabled_many(("feed", "environment_off")) == {
        "feed": True,
        "environment_off": False,
    }
    assert len(reads) == 1


async def test_committed_switch_invalidates_before_expiry(database) -> None:
    sessions, reads = database
    now = [0.0]
    gate = SqlSourceAdmission(sessions, monotonic=lambda: now[0])
    assert await gate.enabled("research_google_news_fa")
    await switch(sessions, "google_news", False)
    # A parent switch applies to its variants at once, with no time-to-live wait.
    assert not await gate.enabled("research_google_news_fa")
    assert not await gate.enabled("google_news")
    await switch(sessions, "google_news", True)
    assert await gate.enabled("research_google_news_fa")
    assert len(reads) == 3


async def test_uncommitted_or_rolled_back_switches_never_stick(database) -> None:
    sessions, _ = database
    gate = SqlSourceAdmission(sessions)
    before = source_control_version()
    async with sessions() as session:
        await SqlSourceControlRepository(session).set("feed", False, NOW, ACTOR)
        assert await gate.enabled("feed")  # other connections cannot see the pending write
        await session.rollback()
    assert source_control_version() > before
    assert await gate.enabled("feed")


async def test_expiry_bounds_writes_made_outside_this_process(database) -> None:
    sessions, reads = database
    now = [100.0]
    gate = SqlSourceAdmission(sessions, ttl_seconds=30, monotonic=lambda: now[0])
    assert await gate.enabled("feed")
    # A table-level insert models another process: no ORM event reaches this cache.
    async with sessions() as session:
        await session.execute(
            insert(SourceControlRow.__table__).values(
                source_id="feed", enabled=False, updated_at=NOW, updated_by=ACTOR
            )
        )
        await session.commit()
    now[0] += 29
    assert await gate.enabled("feed") and len(reads) == 1
    now[0] += 1
    assert not await gate.enabled("feed") and len(reads) == 2


async def test_switch_committed_during_a_reload_is_never_cached(database) -> None:
    sessions, reads = database
    raced = False

    class RacingSession:
        def __init__(self, inner: AsyncSession) -> None:
            self._inner = inner

        async def scalars(self, statement):
            nonlocal raced
            rows = list(await self._inner.scalars(statement))
            if not raced:
                raced = True
                await switch(sessions, "feed", False)  # commits after this SELECT ran
            return rows

    @asynccontextmanager
    async def racing_sessions():
        async with sessions() as session:
            yield RacingSession(session)

    gate = SqlSourceAdmission(racing_sessions)  # type: ignore[arg-type]
    assert await gate.enabled("feed")  # read before the commit; returned, not kept
    assert not await gate.enabled("feed")
    assert len(reads) == 2


async def test_cached_flag_cannot_outlive_an_administrator_disable(
    client: AsyncClient, container: Container, admin: User
) -> None:
    connector = container.connectors[0]
    assert isinstance(connector, FakeConnector)
    reads = count_control_reads(container.engine)
    for _ in range(3):
        assert (await container.scheduler.poll_once(connector)).ok
    # Two admission checks per poll, three polls, one database read.
    assert len(reads) == 1 and connector.calls == 3
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(
        "/api/admin/sources/fake_feed/activation", headers=bearer(token), json={"enabled": False}
    )
    assert response.status_code == 204
    polls = container.health.get("fake_feed").polls
    outcome = await container.scheduler.poll_once(connector)
    assert not outcome.ok and outcome.error == "Disabled by administrator."
    assert connector.calls == 3 and container.health.get("fake_feed").polls == polls
