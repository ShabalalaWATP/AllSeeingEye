"""SQLite admissions and deletions take a writer lock before inspecting profile history."""

import asyncio
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from ai_usage_helpers import add_policy, policy, reservations, summaries
from ase.adapters.persistence import ai_usage_ledger, llm
from ase.adapters.persistence.llm_profile_lock import lock_profile_reference
from ase.container import Container
from ase.domain.ai_usage import AiAttribution
from ase.domain.users import User
from ase.infrastructure.settings import Settings
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_llm_connections import draft


@pytest.fixture
def settings(settings: Settings, tmp_path: Path) -> Settings:
    """Independent sessions must use independent connections, not an in-memory StaticPool."""
    return settings.model_copy(
        update={"database_url": f"sqlite+aiosqlite:///{(tmp_path / 'profile-races.db').as_posix()}"}
    )


@pytest.mark.parametrize("first_operation", ["reserve", "delete"])
async def test_sqlite_parent_lock_precedes_profile_read_and_ledger_mutations(
    client: AsyncClient,
    container: Container,
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
    first_operation: str,
) -> None:
    def enforce_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    event.listen(container.engine.sync_engine, "connect", enforce_foreign_keys)
    # Metadata creation has already opened one pooled connection. Enable it too.
    async with container.engine.connect() as connection:
        await connection.execute(text("PRAGMA foreign_keys=ON"))
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    extra = await draft(client, headers)
    profile_id = UUID(extra["id"])
    allowance = policy(limit=10, tokens=1000)
    await add_policy(container, allowance)
    locked, proceed = asyncio.Event(), asyncio.Event()

    async def operate(session, operation: str) -> None:
        repositories = container.repositories(session)
        if operation == "delete":
            await repositories.llm_profiles.delete(profile_id)
        else:
            await repositories.ai_usage.reserve(
                allowance.id,
                call_id=uuid4(),
                attribution=AiAttribution.actor(admin.id),
                profile_id=profile_id,
                model=extra["model"],
                purpose="connection_test",
                requested_tokens=100,
                now=container.clock.now(),
            )

    async with container.session_factory() as first:

        async def pause_after_parent(session, identity, *, for_delete=False):
            result = await lock_profile_reference(session, identity, for_delete=for_delete)
            if session is first:
                # Pause before any policy/reservation write can accidentally provide the lock.
                locked.set()
                await proceed.wait()
            return result

        monkeypatch.setattr(ai_usage_ledger, "lock_profile_reference", pause_after_parent)
        monkeypatch.setattr(llm, "lock_profile_reference", pause_after_parent)
        pending = asyncio.create_task(operate(first, first_operation))
        try:
            await asyncio.wait_for(locked.wait(), 5)
            opposite = "delete" if first_operation == "reserve" else "reserve"
            async with container.session_factory() as second:
                await second.execute(text("PRAGMA busy_timeout=0"))
                assert await second.scalar(text("PRAGMA foreign_keys")) == 1
                # Fail immediately on real database contention, without timing-based sleeps.
                with pytest.raises(OperationalError) as blocked:
                    await operate(second, opposite)
                assert blocked.value.orig.sqlite_errorcode == sqlite3.SQLITE_BUSY
                await second.rollback()
                proceed.set()
                await asyncio.wait_for(pending, 5)
                await first.commit()
                await operate(second, opposite)
                await second.commit()
        finally:
            proceed.set()
            if not pending.done():
                pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)

    [reserved] = await reservations(container)
    assert reserved.profile_id is None and reserved.model == extra["model"]
    [summary] = await summaries(container, admin.id)
    assert (summary.reserved_requests, summary.reserved_tokens) == (1, 100)
    async with container.session_factory() as session:
        assert await container.repositories(session).llm_profiles.get(profile_id) is None
        assert not (await session.execute(text("PRAGMA foreign_key_check"))).all()
