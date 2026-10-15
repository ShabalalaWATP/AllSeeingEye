"""Maintenance must observe a concurrently renewed TOTP enrolment after locking."""

import asyncio
from datetime import timedelta

from ase.adapters.persistence.totp import AdminTotpRow, SqlTotpRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.container.auth_retention import maintain_authentication
from ase.domain.auth_retention import AuthRetentionPolicy
from auth_retention_helpers import seed
from helpers import USER_EMAIL, USER_PASSWORD, create_user
from token_race_helpers import race_container as race_container  # noqa: PLC0414


async def test_renewal_committed_while_housekeeping_waits_is_retained(race_container, monkeypatch):
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    await seed(
        container,
        AdminTotpRow(
            user_id=user.id, pending_encrypted="expired", pending_expires_at=container.clock.now()
        ),
    )
    owner_locked, release_owner, maintenance_waiting = (
        asyncio.Event(),
        asyncio.Event(),
        asyncio.Event(),
    )
    connections = {}
    postgres = container.engine.dialect.name == "postgresql"
    original_account = SqlUserRepository.lock_by_id
    original_administration = SqlUserRepository.lock_administration

    async def observe(repository):
        connection = await repository._session.connection()
        connections[asyncio.current_task().get_name()] = id(
            connection.sync_connection.connection.dbapi_connection
        )

    async def account(repository, identifier):
        await observe(repository)
        if postgres and asyncio.current_task().get_name() == "maintenance":
            maintenance_waiting.set()
        return await original_account(repository, identifier)

    async def administration(repository):
        await observe(repository)
        if not postgres:
            maintenance_waiting.set()
        await original_administration(repository)

    monkeypatch.setattr(SqlUserRepository, "lock_by_id", account)
    monkeypatch.setattr(SqlUserRepository, "lock_administration", administration)

    async def renew():
        async with container.session_factory() as session:
            await SqlUserRepository(session).lock_by_id(user.id)
            owner_locked.set()
            await asyncio.wait_for(release_owner.wait(), 10)
            assert await SqlTotpRepository(session).begin(
                user.id, "renewed", container.clock.now() + timedelta(minutes=10)
            )
            await session.commit()

    owner = asyncio.create_task(renew(), name="renewal")
    maintenance = None
    try:
        await asyncio.wait_for(owner_locked.wait(), 10)
        maintenance = asyncio.create_task(
            maintain_authentication(
                container.session_factory,
                container.clock.now(),
                AuthRetentionPolicy(),
                dry_run=False,
            ),
            name="maintenance",
        )
        await asyncio.wait_for(maintenance_waiting.wait(), 10)
        release_owner.set()
        await asyncio.wait_for(owner, 10)
        assert (await asyncio.wait_for(maintenance, 10))["pending_totp"] == 0
        assert len(set(connections.values())) == 2
        async with container.session_factory() as session:
            assert (await session.get(AdminTotpRow, user.id)).pending_encrypted == "renewed"
    finally:
        release_owner.set()
        tasks = [owner, *([maintenance] if maintenance else [])]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
