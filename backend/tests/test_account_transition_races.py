"""Account locks prevent stale credential writes and removal of every active admin."""

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.users import SqlUserRepository
from ase.application.auth.current_session import validate_current_session
from ase.application.auth.sessions import SessionFactory
from ase.application.dto import AuthSession, RequestContext
from ase.container import Container
from ase.domain.errors import (
    Forbidden,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidToken,
    Unauthenticated,
)
from ase.domain.tokens import PasswordToken, TokenPurpose
from ase.domain.users import Role, User
from helpers import ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, FakeClock, create_user
from token_race_helpers import CONTEXT
from token_race_helpers import race_container as race_container  # noqa: PLC0414

NEW_PASSWORD = "Replacement-Observatory-Password-2026"


async def reset_secret(container: Container, user: User) -> str:
    secret = container.generator.new_secret()
    now = container.clock.now()
    async with container.session_factory() as session:
        await container.repositories(session).password_tokens.add(
            PasswordToken(
                id=uuid4(),
                user_id=user.id,
                token_hash=container.generator.hash(secret),
                purpose=TokenPurpose.RESET,
                expires_at=now + timedelta(minutes=30),
                used_at=None,
                created_at=now,
            )
        )
        await session.commit()
    return secret


async def test_login_waiting_for_password_change_reads_new_credentials(
    race_container: Container,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    secret = await reset_secret(container, user)
    reached = asyncio.Event()
    release = asyncio.Event()
    original = SqlUserRepository.lock_by_email

    async def pause(self: SqlUserRepository, email: str) -> User | None:
        reached.set()
        await asyncio.wait_for(release.wait(), 10)
        return await original(self, email)

    monkeypatch.setattr(SqlUserRepository, "lock_by_email", pause)

    async def login() -> AuthSession:
        async with container.session_factory() as session:
            return await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)

    task = asyncio.create_task(login())
    try:
        await asyncio.wait_for(reached.wait(), 10)
        async with container.session_factory() as session:
            await container.set_password(session).execute(secret, NEW_PASSWORD, CONTEXT)
        release.set()
        with pytest.raises(InvalidCredentials):
            await task
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)
    async with container.session_factory() as session:
        stored = await container.repositories(session).users.get_by_id(user.id)
        assert stored and stored.security_version == 1
        assert container.hasher.verify(stored.password_hash or "", NEW_PASSWORD)


async def test_password_change_waits_for_login_then_invalidates_issued_session(
    race_container: Container,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    secret = await reset_secret(container, user)
    login_locked = asyncio.Event()
    reset_waiting = asyncio.Event()
    release = asyncio.Event()
    start = SessionFactory.start
    lock = SqlUserRepository.lock_by_id

    async def pause_start(
        self: SessionFactory,
        user: User,
        context: RequestContext,
        *,
        family_id: UUID | None = None,
        parent_id: UUID | None = None,
    ) -> AuthSession:
        login_locked.set()
        await asyncio.wait_for(release.wait(), 10)
        return await start(self, user, context, family_id=family_id, parent_id=parent_id)

    async def observe_reset(self: SqlUserRepository, user_id: UUID) -> User | None:
        reset_waiting.set()
        return await lock(self, user_id)

    monkeypatch.setattr(SessionFactory, "start", pause_start)
    monkeypatch.setattr(SqlUserRepository, "lock_by_id", observe_reset)

    async def login() -> AuthSession:
        async with container.session_factory() as session:
            return await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)

    async def reset() -> None:
        async with container.session_factory() as session:
            await container.set_password(session).execute(secret, NEW_PASSWORD, CONTEXT)

    login_task = asyncio.create_task(login())
    await asyncio.wait_for(login_locked.wait(), 10)
    reset_task = asyncio.create_task(reset())
    try:
        await asyncio.wait_for(reset_waiting.wait(), 10)
        assert not reset_task.done()
        release.set()
        auth = await login_task
        await reset_task
    finally:
        release.set()
        await asyncio.gather(login_task, reset_task, return_exceptions=True)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        stored = await repos.users.get_by_id(user.id)
        assert stored and stored.security_version == 1
        assert container.hasher.verify(stored.password_hash or "", NEW_PASSWORD)
        claims = container.issuer.verify(auth.access.token)
        with pytest.raises(Unauthenticated):
            await validate_current_session(
                claims, repos.users, repos.refresh_tokens, container.clock
            )


@pytest.mark.parametrize("deactivate", [False, True])
async def test_competing_administrators_cannot_remove_each_other(
    race_container: Container,
    deactivate: bool,
) -> None:
    container = race_container
    first = await create_user(
        container, email="first-admin@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    second = await create_user(
        container, email="second-admin@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    barrier = asyncio.Barrier(2)

    async def remove(actor: User, target: User) -> User:
        async with container.session_factory() as session:
            await barrier.wait()
            return await container.update_user(session).execute(
                actor,
                target.id,
                None if deactivate else Role.USER,
                False if deactivate else None,
                CONTEXT,
            )

    outcomes = await asyncio.wait_for(
        asyncio.gather(
            remove(first, second),
            remove(second, first),
            return_exceptions=True,
        ),
        15,
    )
    assert sum(isinstance(outcome, User) for outcome in outcomes) == 1, outcomes
    assert sum(isinstance(outcome, Forbidden) for outcome in outcomes) == 1, outcomes
    async with container.session_factory() as session:
        users = await container.repositories(session).users.list_all()
        assert sum(account.is_admin and account.is_active for account in users) == 1


async def test_stale_administrator_cannot_issue_reset_link_after_demotion(
    race_container: Container,
) -> None:
    container = race_container
    first = await create_user(
        container, email="first-admin@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    second = await create_user(
        container, email="second-admin@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
    )
    async with container.session_factory() as session:
        await container.update_user(session).execute(first, second.id, Role.USER, None, CONTEXT)
    async with container.session_factory() as session:
        with pytest.raises(Forbidden):
            await container.issue_reset_link(session).execute(second, first.id, CONTEXT)


async def test_password_change_invalidates_other_outstanding_reset_links(
    race_container: Container,
) -> None:
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    older = await reset_secret(container, user)
    newer = await reset_secret(container, user)
    async with container.session_factory() as session:
        await container.set_password(session).execute(newer, NEW_PASSWORD, CONTEXT)
    async with container.session_factory() as session:
        with pytest.raises(InvalidToken):
            await container.set_password(session).execute(
                older, "Older-Compromised-Password-42", CONTEXT
            )
    async with container.session_factory() as session:
        stored = await container.repositories(session).users.get_by_id(user.id)
        assert stored and container.hasher.verify(stored.password_hash or "", NEW_PASSWORD)


@pytest.mark.parametrize("refresh", [True, False])
async def test_token_expiry_rechecked_after_waiting_for_account_lock(
    race_container: Container,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
    refresh: bool,
) -> None:
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    if refresh:
        async with container.session_factory() as session:
            auth = await container.login(session).execute(USER_EMAIL, USER_PASSWORD, CONTEXT)
            secret = auth.refresh_secret
    else:
        secret = await reset_secret(container, user)
    lock = SqlUserRepository.lock_by_id

    async def waited(self: SqlUserRepository, identity: UUID) -> User | None:
        current = await lock(self, identity)
        # Model time passing while the operation waited for the database lock.
        clock.advance(timedelta(days=91))
        return current

    monkeypatch.setattr(SqlUserRepository, "lock_by_id", waited)
    async with container.session_factory() as session:
        if refresh:
            with pytest.raises(InvalidRefreshToken):
                await container.refresh(session).execute(secret, CONTEXT)
        else:
            with pytest.raises(InvalidToken):
                await container.set_password(session).execute(secret, NEW_PASSWORD, CONTEXT)
