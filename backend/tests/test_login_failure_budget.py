"""The per-email sign-in budget counts failures only, without weakening guess limits."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, login

WRONG = "wrong-password-value"


@pytest.fixture
def settings(settings, tmp_path):
    # A file database gives each request its own connection, so the account lock is real.
    if settings.database_url.startswith("sqlite"):
        return settings.model_copy(
            update={"database_url": f"sqlite+aiosqlite:///{tmp_path / 'login-budget.db'}"}
        )
    return settings


async def test_successful_sign_ins_do_not_spend_the_email_budget(
    client: AsyncClient, user: User
) -> None:
    for _ in range(4):
        assert (await login(client, USER_EMAIL, WRONG)).status_code == 401
    # Previously each success consumed the same five-per-minute allowance as a guess.
    for _ in range(3):
        assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 200
    assert (await login(client, USER_EMAIL, WRONG)).status_code == 401
    # Five failures exhaust the budget for every caller, including the owner.
    limited = await login(client, USER_EMAIL, USER_PASSWORD)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"


async def test_failures_age_out_so_an_attacker_cannot_hold_the_account(
    client: AsyncClient, user: User, clock: FakeClock
) -> None:
    for _ in range(5):
        assert (await login(client, USER_EMAIL, WRONG)).status_code == 401
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 429
    clock.advance(timedelta(seconds=61))
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 200


async def test_unknown_emails_spend_their_own_budget(client: AsyncClient, user: User) -> None:
    for _ in range(5):
        assert (await login(client, "nobody@example.com", WRONG)).status_code == 401
    assert (await login(client, "nobody@example.com", WRONG)).status_code == 429
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 200


async def test_concurrent_guesses_cannot_overshoot_the_failure_budget(
    client: AsyncClient, user: User, container: Container
) -> None:
    async with asyncio.timeout(60):
        responses = await asyncio.gather(*(login(client, USER_EMAIL, WRONG) for _ in range(8)))
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [401] * 5 + [429] * 3, [response.text for response in responses]
    assert (await login(client, USER_EMAIL, USER_PASSWORD)).status_code == 429
