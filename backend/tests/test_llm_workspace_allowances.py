"""Daily presets feed real admission and preserve all other allowance constraints."""

from datetime import timedelta
from uuid import UUID

import pytest

from ai_usage_helpers import accounting
from ase.api.schemas_llm_workspace import LlmWorkspaceChangeIn
from ase.application.dto import RequestContext
from ase.domain.ai_usage import AiAllowanceExceeded, AiAttribution, AiCallOutcome
from ase.domain.errors import Unauthenticated
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_llm_workspace import allowance_change, apply, model_change, setup_models

POLICIES = "/api/admin/ai-usage/policies"


async def reserve(container, user):
    return await accounting(container).reserve(
        AiAttribution.actor(user.id),
        profile_id=None,
        model="fixture",
        purpose="test",
        requested_tokens=1,
    )


@pytest.mark.parametrize(
    ("preset", "requests", "tokens"),
    [
        ("light", 50, 100_000),
        ("standard", 250, 500_000),
        ("intensive", 1000, 2_000_000),
        ("power", 2500, 5_000_000),
        ("blocked", 0, 0),
    ],
)
async def test_daily_presets_are_exact_and_enforced(
    client, container, admin, user, preset, requests, tokens
):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    result = await apply(client, headers, allowance_change(preset))
    assert result.status_code == 200, result.text
    policy = result.json()["policies"][0]
    assert (policy["request_limit"], policy["token_limit"], policy["period"]) == (
        requests,
        tokens,
        "day",
    )
    if preset == "blocked":
        with pytest.raises(AiAllowanceExceeded):
            await reserve(container, user)
    else:
        batch = await reserve(container, user)
        assert len(batch.reservations) == 1
        assert str(batch.reservations[0].policy_id) == policy["id"]
        await accounting(container).finish(batch, AiCallOutcome.NOT_DISPATCHED)


async def test_edit_and_inherit_preserve_other_periods_and_do_not_reset_usage(
    client, container, admin, user
):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    weekly = await client.post(
        POLICIES, headers=headers, json={"scope": "global", "period": "week", "request_limit": 1}
    )
    monthly = await client.post(
        POLICIES, headers=headers, json={"scope": "global", "period": "month", "request_limit": 10}
    )
    created = await apply(client, headers, allowance_change("light"))
    day = next(item for item in created.json()["policies"] if item["period"] == "day")
    batch = await reserve(container, user)
    await accounting(container).finish(
        batch, AiCallOutcome.COMPLETED, prompt_tokens=1, completion_tokens=1
    )
    changed = await apply(client, headers, allowance_change("power", policy=day))
    assert changed.status_code == 200
    day = next(item for item in changed.json()["policies"] if item["period"] == "day")
    assert day["revision"] == 2
    with pytest.raises(AiAllowanceExceeded):
        await reserve(container, user)  # The exhausted weekly limit still governs.
    inherited = await apply(client, headers, allowance_change("inherit", policy=day))
    assert inherited.status_code == 200, inherited.text
    policies = inherited.json()["policies"]
    assert next(item for item in policies if item["id"] == day["id"])["enabled"] is False
    assert next(item for item in policies if item["period"] == "week") == weekly.json()
    assert next(item for item in policies if item["period"] == "month") == monthly.json()
    with pytest.raises(AiAllowanceExceeded):
        await reserve(container, user)
    # The disabled policy is not reused: a new enabled policy has a new identity.
    restored = await apply(client, headers, allowance_change("standard"))
    assert restored.status_code == 200
    active = next(
        item for item in restored.json()["policies"] if item["period"] == "day" and item["enabled"]
    )
    assert active["id"] != day["id"]


async def test_active_temporary_block_refuses_preset_and_inherit(
    client, container, admin, user, clock
):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await apply(client, headers, allowance_change("light"))
    day = created.json()["policies"][0]
    override = await client.post(
        f"{POLICIES}/{day['id']}/overrides",
        headers=headers,
        json={
            "requests": {"state": "blocked"},
            "tokens": {"state": "inherit"},
            "effective_from": clock.now().isoformat(),
            "expires_at": (clock.now() + timedelta(hours=1)).isoformat(),
        },
    )
    assert override.status_code == 201, override.text
    changed = await apply(client, headers, allowance_change("power", policy=day))
    assert changed.status_code == 422 and "temporary" in changed.text
    with pytest.raises(AiAllowanceExceeded):
        await reserve(container, user)
    rejected = await apply(client, headers, allowance_change("inherit", policy=day))
    assert rejected.status_code == 422 and "temporary" in rejected.text
    overrides = await client.get(f"{POLICIES}/{day['id']}/overrides", headers=headers)
    assert overrides.json()["items"] == [override.json()]
    assert (await client.get(POLICIES, headers=headers)).json() == [day]


@pytest.mark.parametrize("preset", ["blocked", "standard"])
@pytest.mark.parametrize("future", [False, True])
async def test_unlimited_override_refuses_misleading_preset_without_changes(
    client, admin, clock, preset, future
):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await apply(client, headers, allowance_change("light"))
    day = created.json()["policies"][0]
    override = await client.post(
        f"{POLICIES}/{day['id']}/overrides",
        headers=headers,
        json={
            "requests": {"state": "unlimited"},
            "tokens": {"state": "unlimited"},
            "effective_from": (clock.now() + timedelta(hours=int(future))).isoformat(),
            "expires_at": (clock.now() + timedelta(hours=2)).isoformat(),
        },
    )
    assert override.status_code == 201, override.text
    changed = await apply(client, headers, allowance_change(preset, policy=day))
    assert changed.status_code == 422 and "advanced usage controls" in changed.text
    assert (await client.get(POLICIES, headers=headers)).json() == [day]
    overrides = await client.get(f"{POLICIES}/{day['id']}/overrides", headers=headers)
    assert overrides.json()["items"] == [override.json()]


async def test_stale_policy_identity_and_revision_are_rejected(client, admin):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await apply(client, headers, allowance_change("light"))
    day = created.json()["policies"][0]
    assert (await apply(client, headers, allowance_change("power"))).status_code == 422
    newer = await apply(client, headers, allowance_change("standard", policy=day))
    assert newer.status_code == 200
    assert (
        await apply(client, headers, allowance_change("blocked", policy=day))
    ).status_code == 422
    day = newer.json()["policies"][0]
    assert (
        await apply(client, headers, allowance_change("inherit", policy=day))
    ).status_code == 200
    assert (await apply(client, headers, allowance_change("light", policy=day))).status_code == 422


async def test_expired_original_session_rolls_back_entire_workspace(client, container, admin):
    _headers, first, receipt, _, _ = await setup_models(client, container)
    change = model_change(first, receipt)
    change["allowance"] = allowance_change("blocked")["allowance"]

    async def expired():
        raise Unauthenticated()

    async with container.session_factory() as session:
        current = await container.repositories(session).users.get_by_id(admin.id)
        with pytest.raises(Unauthenticated):
            await container.llm_workspace(session).execute(
                current,
                [LlmWorkspaceChangeIn.model_validate(change).to_input()],
                RequestContext(None, None),
                before_save=expired,
            )
        # The service itself rolls back, even if its caller later commits the session.
        await session.commit()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        assert await repos.llm_bindings.list_all() == []
        assert await repos.ai_usage.list_policies() == []
        profile = await repos.llm_profiles.get(UUID(first["id"]))
        assert profile is not None and not profile.enabled
