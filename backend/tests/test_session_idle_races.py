"""Independent transactions cannot race activity into reviving an idle family."""

import asyncio
from datetime import timedelta

import pytest

from ase.adapters.persistence.tokens import SqlRefreshTokenRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.domain.errors import RateLimited, SessionIdleExpired
from ase.domain.session_activity import SessionActivity
from helpers import USER_EMAIL, USER_PASSWORD, create_user
from token_race_helpers import CONTEXT
from token_race_helpers import race_container as race_container  # noqa: PLC0414


async def initial_session(container):
    await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    async with container.session_factory() as session:
        return await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)


async def test_competing_heartbeats_share_the_durable_minute_limit(race_container):
    container = race_container
    initial = await initial_session(container)
    claims = container.issuer.verify(initial.access.token)
    container.clock.advance(timedelta(minutes=1))

    async def heartbeat():
        async with container.session_factory() as session:
            return await container.session_activity(session).execute(claims, CONTEXT)

    results = await asyncio.gather(heartbeat(), heartbeat(), return_exceptions=True)
    assert sum(isinstance(result, SessionActivity) for result in results) == 1
    assert sum(isinstance(result, RateLimited) for result in results) == 1


async def test_heartbeat_waiting_for_account_lock_rechecks_expiry(race_container, monkeypatch):
    container = race_container
    container.settings.session_idle_minutes = 5
    initial = await initial_session(container)
    claims = container.issuer.verify(initial.access.token)
    container.clock.advance(timedelta(minutes=4))
    started = asyncio.Event()
    lock = SqlUserRepository.lock_by_id

    async def observed_lock(repository, user_id):
        started.set()
        return await lock(repository, user_id)

    async def heartbeat():
        async with container.session_factory() as session:
            return await container.session_activity(session).execute(claims, CONTEXT)

    async with container.session_factory() as held:
        await lock(SqlUserRepository(held), claims.user_id)
        monkeypatch.setattr(SqlUserRepository, "lock_by_id", observed_lock)
        pending = asyncio.create_task(heartbeat())
        try:
            await asyncio.wait_for(started.wait(), 2)
            container.clock.advance(timedelta(minutes=1))
            await held.commit()
            with pytest.raises(SessionIdleExpired):
                await asyncio.wait_for(pending, 2)
        finally:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
    async with container.session_factory() as session:
        repo = container.repositories(session).refresh_tokens
        assert not await repo.family_is_active(
            claims.user_id, claims.family_id, container.clock.now()
        )


async def test_heartbeat_storage_read_crossing_deadline_cannot_revive_family(
    race_container, monkeypatch
):
    container = race_container
    container.settings.session_idle_minutes = 5
    initial = await initial_session(container)
    claims = container.issuer.verify(initial.access.token)
    container.clock.advance(timedelta(minutes=5) - timedelta(microseconds=1))
    read = SqlRefreshTokenRepository.activity

    async def delayed_read(repository, user_id, family_id, now):
        result = await read(repository, user_id, family_id, now)
        # The family was live at the database snapshot, but not when it returned.
        container.clock.advance(timedelta(microseconds=1))
        return result

    monkeypatch.setattr(SqlRefreshTokenRepository, "activity", delayed_read)
    async with container.session_factory() as session:
        with pytest.raises(SessionIdleExpired):
            await container.session_activity(session).execute(claims, CONTEXT)
    async with container.session_factory() as session:
        repo = container.repositories(session).refresh_tokens
        assert not await repo.family_is_active(
            claims.user_id, claims.family_id, container.clock.now()
        )
