"""Removing unused models preserves allowance accounting and active connections."""

from collections.abc import AsyncIterator
from dataclasses import replace
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from ai_usage_helpers import accounting, add_policy, policy, reservations, summaries
from ase.container import Container
from ase.domain.ai_usage import AiAttribution, AiCallOutcome, AiReservationStatus
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_llm import FakeGateway
from test_llm_connections import ROOT, activation, draft, proof


@pytest.fixture(autouse=True)
async def enforce_foreign_keys(container: Container) -> AsyncIterator[None]:
    """Exercise PostgreSQL's referential checks on the local SQLite fixture too."""
    sqlite = container.engine.dialect.name == "sqlite"
    if sqlite:
        async with container.engine.connect() as connection:
            await connection.execute(text("PRAGMA foreign_keys=ON"))
    yield
    if sqlite:
        async with container.engine.connect() as connection:
            await connection.execute(text("PRAGMA foreign_keys=OFF"))


@pytest.mark.parametrize("test_ok", [True, False])
async def test_remove_tested_unused_model_preserves_default_and_accounting(
    client: AsyncClient, container: Container, admin: User, test_ok: bool
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    await add_policy(container, policy(limit=10, tokens=None))
    container.llm = FakeGateway()
    default = await draft(client, headers, "Working default")
    receipt = await proof(client, headers, default)
    applied = await client.put(
        f"{ROOT}/connections", headers=headers, json=activation(default, receipt)
    )
    assert applied.status_code == 200
    extra = await draft(client, headers, "Wrong model")
    container.llm = FakeGateway(fail=None if test_ok else "Unknown model")
    tested = await client.post(f"{ROOT}/profiles/{extra['id']}/test", headers=headers)
    assert tested.status_code == 200 and tested.json()["ok"] is test_ok
    before = await reservations(container)
    assert {row.profile_id for row in before} == {UUID(default["id"]), UUID(extra["id"])}
    allowance = await summaries(container, admin.id)
    usage = (await client.get(f"{ROOT}/usage", headers=headers)).json()

    removed = await client.delete(f"{ROOT}/profiles/{extra['id']}", headers=headers)

    assert removed.status_code == 204, removed.text
    profiles = (await client.get(f"{ROOT}/profiles", headers=headers)).json()["items"]
    assert [item["id"] for item in profiles] == [default["id"]]
    bindings = (await client.get(f"{ROOT}/connections", headers=headers)).json()["items"]
    assert bindings == [applied.json()]
    expected = [
        replace(row, profile_id=None) if row.profile_id == UUID(extra["id"]) else row
        for row in before
    ]
    assert await reservations(container) == expected
    assert await summaries(container, admin.id) == allowance
    assert (await client.get(f"{ROOT}/usage", headers=headers)).json() == usage
    # Active assignments remain protected, including their accounting references.
    assert (
        await client.delete(f"{ROOT}/profiles/{default['id']}", headers=headers)
    ).status_code == 422
    assert await reservations(container) == expected


@pytest.mark.parametrize(
    "outcome", [None, AiCallOutcome.COMPLETED, AiCallOutcome.UNKNOWN, AiCallOutcome.NOT_DISPATCHED]
)
async def test_removal_preserves_all_reservation_states_and_later_settlement(
    client: AsyncClient, container: Container, admin: User, outcome: AiCallOutcome | None
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    await add_policy(container, policy(limit=10, tokens=1000))
    extra = await draft(client, headers)
    meter = accounting(container)
    batch = await meter.reserve(
        AiAttribution.actor(admin.id),
        profile_id=UUID(extra["id"]),
        model=extra["model"],
        purpose="connection_test",
        requested_tokens=100,
    )
    if outcome is not None:
        await meter.finish(batch, outcome, prompt_tokens=3, completion_tokens=4)
    [before] = await reservations(container)
    allowance = await summaries(container, admin.id)

    assert (
        await client.delete(f"{ROOT}/profiles/{extra['id']}", headers=headers)
    ).status_code == 204

    assert await reservations(container) == [replace(before, profile_id=None)]
    assert await summaries(container, admin.id) == allowance
    if outcome is None:
        await meter.finish(batch, AiCallOutcome.COMPLETED, prompt_tokens=3, completion_tokens=4)
        [settled] = await reservations(container)
        assert settled.status is AiReservationStatus.SETTLED
        assert settled.actual_tokens == 7 and settled.profile_id is None
        [summary] = await summaries(container, admin.id)
        assert (summary.used_requests, summary.used_tokens, summary.reserved_tokens) == (1, 7, 0)


async def test_stale_model_snapshot_can_still_be_accounted_after_removal(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    await add_policy(container, policy(limit=10, tokens=1000))
    extra = await draft(client, headers)
    assert (
        await client.delete(f"{ROOT}/profiles/{extra['id']}", headers=headers)
    ).status_code == 204
    meter = accounting(container)
    batch = await meter.reserve(
        AiAttribution.actor(admin.id),
        profile_id=UUID(extra["id"]),
        model=extra["model"],
        purpose="previously_selected_model",
        requested_tokens=100,
    )
    await meter.finish(batch, AiCallOutcome.COMPLETED, prompt_tokens=3, completion_tokens=4)
    [settled] = await reservations(container)
    assert settled.profile_id is None and settled.model == extra["model"]
    assert settled.actual_tokens == 7


async def test_rolled_back_removal_keeps_profile_and_accounting_links(
    client: AsyncClient, container: Container, admin: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    await add_policy(container, policy(limit=10, tokens=None))
    container.llm = FakeGateway()
    extra = await draft(client, headers)
    await proof(client, headers, extra)
    before = await reservations(container)
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.delete(UUID(extra["id"]))
        await session.rollback()
    assert await reservations(container) == before
    profiles = (await client.get(f"{ROOT}/profiles", headers=headers)).json()["items"]
    assert [item["id"] for item in profiles] == [extra["id"]]
