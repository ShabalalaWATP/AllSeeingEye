"""Estimated spend, period-aware limits and the one-click default policy set."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ai_usage_helpers import accounting
from ase.domain.ai_defaults import (
    DEFAULT_PERSON_DAILY_TOKENS,
    DEFAULT_POLICY_SET,
    DEFAULT_SITE_DAILY_TOKENS,
    DEFAULT_SITE_MONTHLY_TOKENS,
    DEFAULT_SYSTEM_DAILY_TOKENS,
)
from ase.domain.ai_pricing import AiTokenPrices
from ase.domain.ai_usage import AiAttribution, AiCallOutcome, charged_split
from ase.infrastructure.settings import Settings
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token

LUNA = AiTokenPrices.of(0.20, 1.20)


def test_luna_prices_estimate_recorded_tokens() -> None:
    # Five measured days: about 969,000 tokens, dominated by output.
    assert LUNA.estimate(100_000, 869_000) == Decimal("1.0628")
    assert LUNA.estimate(0, 0) == Decimal("0.0000")
    assert LUNA.configured


def test_a_zero_price_estimates_nothing_rather_than_zero_pounds() -> None:
    free = AiTokenPrices.of(0, 0)
    assert not free.configured
    assert free.estimate(1_000_000, 1_000_000) is None


def test_a_custom_price_is_used_exactly() -> None:
    custom = AiTokenPrices.of(3, 15, "GBP")
    assert custom.currency == "GBP"
    assert custom.estimate(1_000_000, 2_000_000) == Decimal("33.0000")


def test_prices_reject_nonsense() -> None:
    with pytest.raises(ValueError, match="input token price"):
        AiTokenPrices.of(-1, 1)
    with pytest.raises(ValueError, match="three letter code"):
        AiTokenPrices.of(1, 1, "pounds")
    with pytest.raises(ValueError, match="cannot be negative"):
        LUNA.estimate(-1, 0)


def test_settings_carry_the_luna_defaults_and_stay_editable() -> None:
    assert Settings(env="test").ai_token_prices == LUNA
    edited = Settings(
        env="test",
        ai_price_input_per_million=1.5,
        ai_price_output_per_million=7.5,
        ai_price_currency="EUR",
    ).ai_token_prices
    assert edited.estimate(1_000_000, 1_000_000) == Decimal("9.0000")


def test_an_unsplit_charge_is_counted_as_output_so_cost_is_never_understated() -> None:
    assert charged_split(AiCallOutcome.COMPLETED, 100, 900, 5_000) == (100, 900)
    # A completed call with no reported counts falls back to its reservation.
    assert charged_split(AiCallOutcome.COMPLETED, None, None, 5_000) == (0, 5_000)
    assert charged_split(AiCallOutcome.FAILED, 40, None, 5_000) == (40, 0)
    assert charged_split(AiCallOutcome.NOT_DISPATCHED, 40, 50, 5_000) == (0, 0)


async def test_recorded_totals_split_input_from_output(container, user):
    ledger = accounting(container)
    batch = await ledger.reserve(
        AiAttribution.actor(user.id),
        profile_id=None,
        model="fixture-model",
        purpose="report",
        requested_tokens=500,
    )
    await ledger.finish(batch, AiCallOutcome.COMPLETED, prompt_tokens=120, completion_tokens=880)
    async with container.session_factory() as session:
        totals = await container.repositories(session).ai_usage.account_totals(
            user.id, container.clock.now()
        )
    assert (totals.used_input_tokens, totals.used_output_tokens) == (120, 880)
    assert totals.used_tokens == totals.used_input_tokens + totals.used_output_tokens
    estimate = LUNA.estimate(totals.used_input_tokens, totals.used_output_tokens)
    assert estimate == Decimal("0.0011")  # 120 input at 0.20 plus 880 output at 1.20


async def test_personal_summary_shows_estimated_spend_beside_tokens(client, container, user):
    ledger = accounting(container)
    batch = await ledger.reserve(
        AiAttribution.actor(user.id),
        profile_id=None,
        model="fixture-model",
        purpose="report",
        requested_tokens=500,
    )
    await ledger.finish(batch, AiCallOutcome.COMPLETED, prompt_tokens=1000, completion_tokens=2000)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/ai-usage/me", headers=bearer(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["observed"]["used_input_tokens"] == 1000
    assert body["observed"]["used_output_tokens"] == 2000
    assert body["observed"]["estimated_cost"] == "0.0026"
    assert body["prices"] == {
        "input_per_million": 0.20,
        "output_per_million": 1.20,
        "currency": "USD",
        "configured": True,
    }


async def test_one_target_may_carry_a_daily_and_a_monthly_limit(client, admin, user):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    for period, tokens in (("day", 1000), ("month", 20000)):
        created = await client.post(
            "/api/admin/ai-usage/policies",
            headers=bearer(token),
            json={
                "scope": "user",
                "target_id": str(user.id),
                "period": period,
                "token_limit": tokens,
            },
        )
        assert created.status_code == 201, created.text
    duplicate = await client.post(
        "/api/admin/ai-usage/policies",
        headers=bearer(token),
        json={"scope": "user", "target_id": str(user.id), "period": "day", "token_limit": 5},
    )
    assert duplicate.status_code == 409
    preview = await client.get(
        f"/api/admin/ai-usage/preview?user_id={user.id}", headers=bearer(token)
    )
    assert preview.status_code == 200, preview.text
    assert sorted(item["policy"]["period"] for item in preview.json()["items"]) == ["day", "month"]


async def test_preview_names_the_model_a_person_would_use(client, admin, user):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    preview = await client.get(
        f"/api/admin/ai-usage/preview?user_id={user.id}", headers=bearer(token)
    )
    assert preview.status_code == 200, preview.text
    model = preview.json()["model"]
    # No connection is configured in tests, so the reason is shown rather than a model.
    assert model["unavailable"]
    assert model["profile_id"] is None
    assert "api_key" not in preview.text and "base_url" not in preview.text


async def test_defaults_are_suggested_before_they_are_applied(client, admin, user):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    suggested = await client.get("/api/admin/ai-usage/defaults", headers=bearer(token))
    assert suggested.status_code == 200, suggested.text
    body = suggested.json()
    assert body["enforcing"] is False  # nothing is capped until a policy exists
    limits = {(item["scope"], item["period"]): item["token_limit"] for item in body["items"]}
    assert limits[("global", "day")] == DEFAULT_SITE_DAILY_TOKENS
    assert limits[("global", "month")] == DEFAULT_SITE_MONTHLY_TOKENS
    assert limits[("system", "day")] == DEFAULT_SYSTEM_DAILY_TOKENS
    assert limits[("user", "day")] == DEFAULT_PERSON_DAILY_TOKENS
    assert not any(item["already_configured"] for item in body["items"])
    # Previewing alone must never write a policy.
    assert (await client.get("/api/admin/ai-usage/policies", headers=bearer(token))).json() == []


async def test_applying_defaults_is_audited_and_never_overwrites_an_existing_policy(
    client, admin, user
):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    chosen = await client.post(
        "/api/admin/ai-usage/policies",
        headers=bearer(token),
        json={"scope": "global", "period": "day", "token_limit": 42},
    )
    assert chosen.status_code == 201, chosen.text
    applied = await client.post("/api/admin/ai-usage/defaults", headers=bearer(token))
    assert applied.status_code == 201, applied.text
    created = applied.json()["created"]
    # One suggestion per named default, plus one per active account, less the one kept.
    assert len(created) == len(DEFAULT_POLICY_SET) - 1 + 1  # admin and user accounts
    policies = (await client.get("/api/admin/ai-usage/policies", headers=bearer(token))).json()
    kept = [item for item in policies if item["scope"] == "global" and item["period"] == "day"]
    assert [item["token_limit"] for item in kept] == [42]
    repeated = await client.post("/api/admin/ai-usage/defaults", headers=bearer(token))
    assert repeated.status_code == 201 and repeated.json()["created"] == []
    audit = await client.get("/api/admin/audit-log?limit=50", headers=bearer(token))
    assert audit.status_code == 200, audit.text
    assert any(item["action"] == "ai_usage_defaults_applied" for item in audit.json()["items"])


async def test_default_policies_require_an_administrator(client, user):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (
        await client.get("/api/admin/ai-usage/defaults", headers=bearer(token))
    ).status_code == 403
    assert (
        await client.post("/api/admin/ai-usage/defaults", headers=bearer(token))
    ).status_code == 403
