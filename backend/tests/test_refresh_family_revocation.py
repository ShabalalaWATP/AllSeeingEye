"""A revoked family stays invalid even when a descendant misses the revocation UPDATE."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from ase.adapters.persistence.models import RefreshTokenRow
from ase.adapters.persistence.token_families import (
    REVOCATION_RETENTION,
    RefreshFamilyRevocationRow,
    prune_revoked_families,
)
from ase.application.auth.sessions import SessionFactory
from ase.application.dto import AuthSession, RequestContext
from ase.container import Container
from ase.domain.errors import InvalidRefreshToken
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, create_user
from token_race_helpers import CONTEXT
from token_race_helpers import race_container as race_container  # noqa: PLC0414


@pytest.mark.parametrize("revoke_all", [False, True])
async def test_late_descendant_cannot_refresh_after_revocation(
    race_container: Container,
    revoke_all: bool,
) -> None:
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    async with container.session_factory() as session:
        initial = await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)
        repo = container.repositories(session).refresh_tokens
        root = await repo.get_by_hash(container.generator.hash(initial.refresh_secret))
        assert root is not None
    async with container.session_factory() as session:
        repo = container.repositories(session).refresh_tokens
        if revoke_all:
            await repo.revoke_all_for_user(user.id, container.clock.now())
        else:
            await repo.revoke_family(root.family_id, container.clock.now())
        await session.commit()
    # A separate transaction inserts the descendant which the UPDATE did not see.
    # The PostgreSQL test below recreates the real overlapping transactions.
    late_secret = container.generator.new_secret()
    late = replace(
        root,
        id=uuid4(),
        parent_id=root.id,
        token_hash=container.generator.hash(late_secret),
        revoked_at=None,
    )
    async with container.session_factory() as session:
        await container.repositories(session).refresh_tokens.add(late)
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(InvalidRefreshToken):
            await container.refresh(session).execute(late_secret, CONTEXT)
        markers = list(await session.scalars(select(RefreshFamilyRevocationRow)))
        assert len(markers) == 1
        assert markers[0].family_id == root.family_id
        tokens = list(await session.scalars(select(RefreshTokenRow)))
        assert len(tokens) == 2
        assert all(token.revoked_at is not None for token in tokens)


async def test_revocation_marker_rollback_and_safe_retention(race_container: Container) -> None:
    container = race_container
    await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    now = container.clock.now()
    async with container.session_factory() as session:
        initial = await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)
        repo = container.repositories(session).refresh_tokens
        root = await repo.get_by_hash(container.generator.hash(initial.refresh_secret))
        assert root is not None
        await repo.revoke_family(root.family_id, now)
        await session.rollback()
    async with container.session_factory() as session:
        assert await session.scalar(select(RefreshFamilyRevocationRow)) is None
        repo = container.repositories(session).refresh_tokens
        assert await repo.consume(root.id, now)
        await repo.revoke_family(root.family_id, now)
        await session.commit()
    async with container.session_factory() as session:
        await prune_revoked_families(session, now + timedelta(days=15))
        assert await session.scalar(select(RefreshFamilyRevocationRow)) is not None
        assert await session.get(RefreshTokenRow, root.id) is not None
        # Even an old marker is retained if a token has not expired.
        row = await session.get(RefreshTokenRow, root.id)
        assert row is not None
        row.expires_at = now + REVOCATION_RETENTION + timedelta(days=1)
        await session.commit()
        await prune_revoked_families(session, now + REVOCATION_RETENTION)
        assert await session.scalar(select(RefreshFamilyRevocationRow)) is not None
        await prune_revoked_families(session, now + REVOCATION_RETENTION + timedelta(days=1))
        assert await session.scalar(select(RefreshFamilyRevocationRow)) is None
        assert await session.get(RefreshTokenRow, root.id) is None
        await session.commit()


async def test_postgres_refresh_interleaves_with_family_revocation(
    race_container: Container,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = race_container
    if container.engine.dialect.name != "postgresql":
        pytest.skip("Set ASE_TOKEN_RACE_TEST_URL to an owned PostgreSQL test database.")
    await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    async with container.session_factory() as session:
        initial = await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)
        child = await container.refresh(session).execute(initial.refresh_secret, CONTEXT)
        child_token = await container.repositories(session).refresh_tokens.get_by_hash(
            container.generator.hash(child.refresh_secret),
        )
        assert child_token is not None
    consumed = asyncio.Event()
    permit_insert = asyncio.Event()
    start = SessionFactory.start

    async def pause_after_consume(
        self: SessionFactory,
        user: User,
        context: RequestContext,
        *,
        family_id: UUID | None = None,
        parent_id: UUID | None = None,
    ) -> AuthSession:
        if parent_id == child_token.id:
            consumed.set()
            await asyncio.wait_for(permit_insert.wait(), 10)
        return await start(self, user, context, family_id=family_id, parent_id=parent_id)

    monkeypatch.setattr(SessionFactory, "start", pause_after_consume)

    async def refresh_child() -> AuthSession:
        async with container.session_factory() as session:
            return await container.refresh(session).execute(child.refresh_secret, CONTEXT)

    async def replay_root() -> None:
        async with container.session_factory() as session:
            await session.execute(text("SET application_name = 'ase_family_revocation_test'"))
            with pytest.raises(InvalidRefreshToken):
                await container.refresh(session).execute(initial.refresh_secret, CONTEXT)

    child_task = asyncio.create_task(refresh_child())
    await asyncio.wait_for(consumed.wait(), 10)
    replay_task = asyncio.create_task(replay_root())
    try:
        async with asyncio.timeout(10), container.session_factory() as observer:
            while not await observer.scalar(
                text(
                    "SELECT 1 FROM pg_stat_activity "
                    "WHERE application_name = 'ase_family_revocation_test' "
                    "AND wait_event_type = 'Lock'",
                )
            ):
                await observer.commit()
                await asyncio.sleep(0.01)
        permit_insert.set()
        grandchild = await child_task
        await replay_task
    finally:
        permit_insert.set()
        await asyncio.gather(child_task, replay_task, return_exceptions=True)
    async with container.session_factory() as session:
        row = await container.repositories(session).refresh_tokens.get_by_hash(
            container.generator.hash(grandchild.refresh_secret),
        )
        # Its insert really was outside the UPDATE snapshot, yet its family is dead.
        assert row is not None and row.revoked_at is None
        with pytest.raises(InvalidRefreshToken):
            await container.refresh(session).execute(grandchild.refresh_secret, CONTEXT)
