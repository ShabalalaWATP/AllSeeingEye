"""One or two accounts cannot hold the semantic search slot or call budget for everyone."""

from __future__ import annotations

import asyncio

import pytest

from ase.application.reports.search_slots import (
    EMBEDDING_CALLS_GLOBAL,
    EMBEDDING_CALLS_PER_USER,
    EMBEDDING_WINDOW_SECONDS,
    SearchSlots,
)
from ase.container import Container
from ase.domain.errors import RateLimited
from ase.domain.users import User
from helpers import create_user
from report_search_helpers import FakeEmbeddings, add_profile, add_report, service


async def _other(container: Container) -> User:
    return await create_user(container, email="second-analyst@example.com", password=None)


async def test_slots_admit_one_query_per_account_within_a_shared_cap(
    container: Container, user: User
) -> None:
    slots = SearchSlots(shared=2)
    other = await _other(container)
    third = await create_user(container, email="third-analyst@example.com", password=None)
    async with slots.claim(user.id):
        with pytest.raises(RateLimited):
            async with slots.claim(user.id):
                pass
        async with slots.claim(other.id):
            # The shared backstop still bounds total concurrency.
            with pytest.raises(RateLimited):
                async with slots.claim(third.id):
                    pass
    # Slots are released even when the query fails.
    with pytest.raises(ValueError):
        async with slots.claim(user.id):
            raise ValueError("query failed")
    async with slots.claim(user.id), slots.claim(third.id):
        pass


async def test_an_in_flight_query_blocks_only_its_own_account(
    container: Container, user: User
) -> None:
    gateway = FakeEmbeddings()
    slots = SearchSlots()
    other = await _other(container)
    async with container.session_factory() as session:
        await add_profile(container, session)
        await add_report(container, session, user)
        await add_report(container, session, other, "Maritime other")
        await service(container, session, gateway).index(user)
        await service(container, session, gateway).index(other)
    started, release = asyncio.Event(), asyncio.Event()

    async def hold() -> None:
        started.set()
        await release.wait()

    gateway.during_call = hold
    async with container.session_factory() as first_session:
        first = asyncio.create_task(
            service(container, first_session, gateway, slots=slots).query(user, "maritime")
        )
        await started.wait()
        gateway.during_call = None
        async with container.session_factory() as session:
            with pytest.raises(RateLimited):
                await service(container, session, gateway, slots=slots).query(user, "again")
        async with container.session_factory() as session:
            result = await service(container, session, gateway, slots=slots).query(
                other, "maritime"
            )
            assert [hit.report.created_by for hit in result.items] == [other.id]
        release.set()
        assert len((await first).items) == 1


async def test_one_account_cannot_spend_the_shared_embedding_budget(
    container: Container, user: User
) -> None:
    gateway = FakeEmbeddings()
    other = await _other(container)
    async with container.session_factory() as session:
        await add_profile(container, session)
        await add_report(container, session, user)
        await add_report(container, session, other, "Maritime other")
        search = service(container, session, gateway)
        await search.index(user)
        await search.index(other)
        for _ in range(EMBEDDING_CALLS_PER_USER - 1):
            await search.query(user, "maritime")
        with pytest.raises(RateLimited):
            await search.query(user, "over budget")
        # The heavy account used its whole allowance; everyone else still has theirs.
        assert (await search.query(other, "maritime")).items
        global_used = EMBEDDING_CALLS_PER_USER + 2
        assert (
            container.limiter.peek("embedding:global", global_used + 1, EMBEDDING_WINDOW_SECONDS)
            is None
        )
        assert (
            container.limiter.peek("embedding:global", global_used, EMBEDDING_WINDOW_SECONDS)
            is not None
        )
        # A refusal by one bucket spends nothing from the other.
        for _ in range(EMBEDDING_CALLS_GLOBAL - global_used):
            container.limiter.hit("embedding:global", EMBEDDING_CALLS_GLOBAL, 3600)
        with pytest.raises(RateLimited):
            await search.query(other, "shared backstop")
        assert (
            container.limiter.peek(f"embedding:user:{other.id}", 3, EMBEDDING_WINDOW_SECONDS)
            is None
        )
