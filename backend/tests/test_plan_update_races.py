"""Competing plan edits cannot both overwrite one revision (file SQLite, or PostgreSQL in CI)."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.persistence.direction import SqlPlanRepository
from ase.application.direction.plans import PirInput, PlanInput, SirInput
from ase.container import Container
from ase.domain.errors import Conflict
from helpers import FakeClock, create_user
from token_race_helpers import CONTEXT
from token_race_helpers import race_container as race_container  # noqa: PLC0414


def _input(name: str) -> PlanInput:
    return PlanInput(name, pirs=(PirInput("Question", (SirInput("Signal", ("border",)),)),))


async def test_two_competing_edits_of_one_revision_cannot_both_win(
    race_container: Container,
) -> None:
    container = race_container
    owner = await create_user(container, email="owner@example.com", password=None)
    async with container.session_factory() as session:
        created = await container.create_plan(session).execute(owner, _input("Start"), CONTEXT)

    async def edit(name: str) -> str:
        async with container.session_factory() as session:
            saved = await container.update_plan(session).execute(
                owner, created.id, _input(name), created.updated_at, CONTEXT
            )
            return saved.name

    results = await asyncio.gather(edit("Left"), edit("Right"), return_exceptions=True)
    winners = [result for result in results if isinstance(result, str)]
    assert len(winners) == 1, results
    assert sum(isinstance(result, Conflict) for result in results) == 1, results
    async with container.session_factory() as session:
        stored = await container.repositories(session).plans.get(created.id)
    assert stored is not None and stored.name == winners[0]
    assert stored.updated_at > created.updated_at


async def test_the_conditional_write_is_atomic_across_connections(
    race_container: Container,
) -> None:
    container = race_container
    owner = await create_user(container, email="owner@example.com", password=None)
    async with container.session_factory() as session:
        created = await container.create_plan(session).execute(owner, _input("Start"), CONTEXT)
    expected = created.updated_at
    later = expected + timedelta(seconds=1)
    first_written, second_started = asyncio.Event(), asyncio.Event()

    async def first() -> bool:
        async with container.session_factory() as session:
            saved = await SqlPlanRepository(session).save_if_unchanged(
                replace(created, name="First", updated_at=later), expected
            )
            first_written.set()
            await asyncio.wait_for(second_started.wait(), 10)
            # Give the competing UPDATE time to queue behind this uncommitted write.
            await asyncio.sleep(0.2)
            await session.commit()
            return saved

    async def second() -> bool:
        await asyncio.wait_for(first_written.wait(), 10)
        async with container.session_factory() as session:
            second_started.set()
            saved = await SqlPlanRepository(session).save_if_unchanged(
                replace(created, name="Second", updated_at=later), expected
            )
            await session.commit()
            return saved

    assert await asyncio.wait_for(asyncio.gather(first(), second()), 30) == [True, False]
    async with container.session_factory() as session:
        stored = await container.repositories(session).plans.get(created.id)
    assert stored is not None and stored.name == "First"


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(microseconds=-1)])
async def test_a_new_revision_always_moves_forward(
    race_container: Container, clock: FakeClock, delta: timedelta
) -> None:
    container = race_container
    owner = await create_user(container, email="owner@example.com", password=None)
    async with container.session_factory() as session:
        created = await container.create_plan(session).execute(owner, _input("Start"), CONTEXT)
    clock.advance(delta)
    async with container.session_factory() as session:
        saved = await container.update_plan(session).execute(
            owner, created.id, _input("Next"), created.updated_at, CONTEXT
        )
    assert saved.updated_at > created.updated_at
