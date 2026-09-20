"""PostgreSQL admission and profile removal cannot leave dangling usage references."""

import asyncio
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from ai_usage_helpers import add_policy, policy, reservations, summaries
from ase.adapters.persistence.ai_usage_models import AiUsageReservationRow
from ase.container import Container
from ase.domain.ai_usage import AiAttribution
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_llm import FakeGateway
from test_llm_connections import ROOT, draft, proof


@pytest.mark.parametrize("first_operation", ["reserve", "delete"])
async def test_admission_and_removal_serialise_in_both_orders(
    client: AsyncClient, container: Container, admin: User, first_operation: str
) -> None:
    if container.engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks and independent connections.")
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    extra = await draft(client, headers)
    profile_id = UUID(extra["id"])
    allowance = policy(limit=10, tokens=1000)
    await add_policy(container, allowance)

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

    started = asyncio.Event()
    waiting_pid = None

    async def competing_operation() -> None:
        nonlocal waiting_pid
        async with container.session_factory() as session:
            waiting_pid = await session.scalar(text("SELECT pg_backend_pid()"))
            started.set()
            await operate(session, "delete" if first_operation == "reserve" else "reserve")
            await session.commit()

    async with container.session_factory() as first:
        await operate(first, first_operation)
        competing = asyncio.create_task(competing_operation())
        try:
            await asyncio.wait_for(started.wait(), 5)
            # Observe the database lock, rather than inferring blocking from a sleep.
            async with asyncio.timeout(5):
                async with container.session_factory() as observer:
                    while not await observer.scalar(
                        text("SELECT cardinality(pg_blocking_pids(:pid))"),
                        {"pid": waiting_pid},
                    ):
                        await asyncio.sleep(0.01)
            await first.commit()
            await asyncio.wait_for(competing, 5)
        finally:
            if not competing.done():
                competing.cancel()
            await asyncio.gather(competing, return_exceptions=True)

    [reserved] = await reservations(container)
    assert reserved.profile_id is None and reserved.model == extra["model"]
    [summary] = await summaries(container, admin.id)
    assert (summary.reserved_requests, summary.reserved_tokens) == (1, 100)
    async with container.session_factory() as session:
        assert await container.repositories(session).llm_profiles.get(profile_id) is None


async def test_busy_accounting_returns_retryable_conflict_without_partial_removal(
    client: AsyncClient, container: Container, admin: User
) -> None:
    if container.engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks and independent connections.")
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    await add_policy(container, policy(limit=10, tokens=None))
    container.llm = FakeGateway()
    extra = await draft(client, headers)
    await proof(client, headers, extra)
    before = await reservations(container)
    profile_id = UUID(extra["id"])
    async with container.session_factory() as settlement:
        await settlement.execute(
            select(AiUsageReservationRow.id)
            .where(AiUsageReservationRow.profile_id == profile_id)
            .with_for_update()
        )
        response = await asyncio.wait_for(
            client.delete(f"{ROOT}/profiles/{profile_id}", headers=headers), 5
        )
        assert response.status_code == 409 and "Try removing it again" in response.text
        await settlement.commit()
    assert await reservations(container) == before
    async with container.session_factory() as session:
        assert await container.repositories(session).llm_profiles.get(profile_id) is not None
    assert (
        await client.delete(f"{ROOT}/profiles/{profile_id}", headers=headers)
    ).status_code == 204
