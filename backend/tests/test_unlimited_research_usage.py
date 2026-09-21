"""Unlimited research keeps an honest usage ledger and all independent provider budgets."""

from datetime import timedelta
from uuid import uuid4

import pytest

from ai_usage_helpers import add_policy, policy
from ase.application.dto import RequestContext
from ase.application.ports.feeds import EventQuery
from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest
from ase.domain.research_usage import ResearchUsageLimit
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, filled_store
from report_job_api_helpers import prepared, submit


@pytest.fixture(name="settings")
def unlimited_settings(settings, tmp_path):
    # Paid accounting uses separate sessions. Preserve the CI PostgreSQL test database.
    if settings.database_url.startswith("postgresql"):
        return settings
    return settings.model_copy(
        update={"database_url": f"sqlite+aiosqlite:///{(tmp_path / 'unlimited.sqlite').as_posix()}"}
    )


async def _assign(container, admin, user, tier=5, revision=0):
    async with container.session_factory() as session:
        return await container.research_usage(session).assign(
            admin, user.id, tier, revision, RequestContext()
        )


async def _consume(container, user, count):
    async with container.session_factory() as session:
        for _ in range(count):
            await container.research_usage(session).admit(user, None)


async def _allowance(container, user):
    async with container.session_factory() as session:
        return await container.research_usage(session).me(user)


async def test_unlimited_exceeds_daily_tiers_and_downgrades_keep_both_periods(
    container, admin, user, clock
):
    await _consume(container, user, 4)
    upgraded = await _assign(container, admin, user)
    assert upgraded.used == 4 and upgraded.limit is upgraded.remaining is None
    assert upgraded.period == "day"
    await _consume(container, user, 33)
    assert (await _allowance(container, user)).used == 37
    limited = await _assign(container, admin, user, tier=4, revision=1)
    assert limited.used == 37 and limited.remaining == 0
    with pytest.raises(ResearchUsageLimit):
        await _consume(container, user, 1)
    clock.advance(timedelta(days=1))
    weekly = await _assign(container, admin, user, tier=1, revision=2)
    assert weekly.used == 37 and weekly.remaining == 0
    with pytest.raises(ResearchUsageLimit):
        await _consume(container, user, 1)
    resumed = await _assign(container, admin, user, tier=5, revision=3)
    assert resumed.used == 0 and resumed.remaining is None
    await _consume(container, user, 1)
    weekly = await _assign(container, admin, user, tier=1, revision=4)
    assert weekly.used == 38


async def test_unlimited_api_uses_null_limits_and_allows_admin_self_assignment(
    client, container, admin, user
):
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    user_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    for target in (user, admin):
        response = await client.put(
            f"/api/admin/users/{target.id}/research-tier",
            headers=admin_headers,
            json={"tier": 5, "expected_revision": 0},
        )
        assert response.status_code == 200, response.text
        assert response.json()["limit"] is response.json()["remaining"] is None
        assert response.json()["tier"] == 5 and response.json()["period"] == "day"
    await _consume(container, user, 1)
    own = await client.get("/api/research-usage/me", headers=user_headers)
    assert own.status_code == 200 and own.json()["used"] == 1
    assert own.json()["limit"] is own.json()["remaining"] is None
    listing = await client.get("/api/admin/research-usage", headers=admin_headers)
    assert listing.json()["tiers"][-1] == {
        "tier": 5,
        "label": "Level 5",
        "limit": None,
        "period": "day",
    }


async def test_unlimited_durable_admission_after_32_runs_still_counts_once(
    client, container, admin, user
):
    _, headers = await prepared(container, client)
    await _assign(container, admin, user)
    await _consume(container, user, 32)
    request_id = uuid4()
    first = await submit(client, headers, request_id=request_id)
    repeated = await submit(client, headers, request_id=request_id)
    assert repeated.json()["id"] == first.json()["id"]
    allowance = await _allowance(container, user)
    assert allowance.used == 33 and allowance.remaining is None


async def test_unlimited_synchronous_generation_is_admitted_and_still_counted(
    container, admin, user, monkeypatch
):
    await seed_legacy_profile(container, PROFILE)
    await _assign(container, admin, user)
    await _consume(container, user, 32)
    async with container.session_factory() as session:
        generator = container.generate_report(session)

        async def fail(*args, **kwargs):
            assert not session.in_transaction()
            raise InvalidRequest("Synthetic production failure")

        monkeypatch.setattr(generator._producer, "produce_with_claims", fail)
        with pytest.raises(InvalidRequest, match="Synthetic production failure"):
            await generator.execute(user, ReportRequest("intsum"), RequestContext())
    assert (await _allowance(container, user)).used == 33


@pytest.mark.parametrize("request_limit,token_limit", [(0, None), (None, 0)])
async def test_unlimited_research_does_not_bypass_site_request_or_token_budget(
    client, container, admin, user, request_limit, token_limit
):
    await seed_legacy_profile(container, PROFILE)
    await _assign(container, admin, user)
    await add_policy(container, policy(limit=request_limit, tokens=token_limit))
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    container.llm = gateway = ScriptedGateway("{}")
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.post("/api/reports", headers=headers, json={"template": "intsum"})
    assert response.status_code == 429, response.text
    assert response.json()["error"]["code"] == "ai_usage_limit"
    assert gateway.requests == []
    allowance = await _allowance(container, user)
    assert allowance.used == 1 and allowance.remaining is None
