"""Dated temporary overrides: explicit states, precedence, expiry and administration."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from ai_usage_helpers import NOW, accounting, add_policy, policy, summaries
from ase.application.ai_usage_admin import AiOverrideInput, AiUsagePolicyAdmin
from ase.domain.ai_usage import AiAllowanceExceeded, AiAttribution
from ase.domain.ai_usage_overrides import (
    MAX_OPEN_OVERRIDES,
    AiLimitOverride,
    AiLimitState,
    AiPolicyOverride,
    active_override,
)
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token

INHERIT = AiLimitOverride(AiLimitState.INHERIT)
UNLIMITED = AiLimitOverride(AiLimitState.UNLIMITED)
BLOCKED = AiLimitOverride(AiLimitState.BLOCKED)


def limit(value: int) -> AiLimitOverride:
    return AiLimitOverride(AiLimitState.LIMIT, value)


def override(requests, tokens, *, start=NOW, hours=24, created=NOW, revoked=None):
    return AiPolicyOverride(
        uuid4(),
        uuid4(),
        requests,
        tokens,
        start,
        start + timedelta(hours=hours),
        uuid4(),
        created,
        revoked,
    )


def test_limit_states_are_explicit_and_zero_never_means_unlimited():
    assert INHERIT.apply(7) == 7 and INHERIT.apply(None) is None
    assert UNLIMITED.apply(7) is None
    assert BLOCKED.apply(None) == 0
    assert limit(0).apply(None) == 0
    with pytest.raises(InvalidRequest):
        AiLimitOverride(AiLimitState.LIMIT)
    with pytest.raises(InvalidRequest):
        AiLimitOverride(AiLimitState.UNLIMITED, 0)
    with pytest.raises(InvalidRequest):
        override(INHERIT, INHERIT, hours=0)
    with pytest.raises(InvalidRequest):
        override(INHERIT, INHERIT, hours=24 * 400)


def test_latest_active_override_wins_and_expiry_or_revocation_ends_it():
    older = override(limit(1), INHERIT)
    newer = override(BLOCKED, INHERIT, created=NOW + timedelta(minutes=1))
    revoked = override(UNLIMITED, INHERIT, created=NOW + timedelta(minutes=2), revoked=NOW)
    later = override(UNLIMITED, INHERIT, start=NOW + timedelta(days=3))
    items = [older, newer, revoked, later]
    assert active_override(items, NOW + timedelta(hours=1)) is newer
    assert active_override(items, NOW + timedelta(hours=25)) is None
    assert active_override(items, NOW + timedelta(days=3, hours=1)) is later


async def test_active_override_beats_base_policy_until_it_expires(container, user, admin, clock):
    base = policy(limit=1, tokens=None)
    await add_policy(container, base)
    ledger = accounting(container)
    attribution = AiAttribution.actor(user.id)

    async def reserve():
        return await ledger.reserve(
            attribution, profile_id=None, model="m", purpose="t", requested_tokens=1
        )

    async with container.session_factory() as session:
        service = AiUsagePolicyAdmin(container.repositories(session).ai_usage, container.clock)
        created = await service.create_override(
            admin,
            base.id,
            AiOverrideInput(
                limit(3),
                BLOCKED,
                clock.now() - timedelta(minutes=1),
                clock.now() + timedelta(hours=2),
            ),
        )
        await session.commit()
    # Tokens are blocked by the override even though the base policy has no token ceiling.
    with pytest.raises(AiAllowanceExceeded):
        await reserve()
    async with container.session_factory() as session:
        service = AiUsagePolicyAdmin(container.repositories(session).ai_usage, container.clock)
        await service.revoke_override(admin, created.id)
        await service.create_override(
            admin,
            base.id,
            AiOverrideInput(
                limit(3),
                INHERIT,
                clock.now() - timedelta(minutes=1),
                clock.now() + timedelta(hours=2),
            ),
        )
        await session.commit()
    for _ in range(3):
        await reserve()
    [summary] = await summaries(container, user.id)
    assert summary.request_limit == 3 and summary.override is not None
    with pytest.raises(AiAllowanceExceeded):
        await reserve()
    clock.advance(timedelta(hours=3))
    [summary] = await summaries(container, user.id)
    assert summary.override is None and summary.request_limit == 1


async def test_override_administration_is_admin_only_and_bounded(container, user, admin):
    base = policy()
    await add_policy(container, base)
    window = AiOverrideInput(UNLIMITED, INHERIT, NOW, NOW + timedelta(days=400))
    async with container.session_factory() as session:
        service = AiUsagePolicyAdmin(container.repositories(session).ai_usage, container.clock)
        with pytest.raises(Forbidden):
            await service.create_override(user, base.id, window)
        with pytest.raises(NotFound):
            await service.create_override(admin, uuid4(), window)
        now = container.clock.now()
        with pytest.raises(InvalidRequest):
            await service.create_override(
                admin, base.id, AiOverrideInput(UNLIMITED, INHERIT, now - timedelta(days=2), now)
            )
        valid = AiOverrideInput(UNLIMITED, INHERIT, now, now + timedelta(days=1))
        for _ in range(MAX_OPEN_OVERRIDES):
            await service.create_override(admin, base.id, valid)
        with pytest.raises(Conflict):
            await service.create_override(admin, base.id, valid)
        assert len(await service.list_overrides(admin, base.id)) == MAX_OPEN_OVERRIDES


async def test_override_api_creates_lists_and_revokes_with_audit(client, container, admin, user):
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post(
        "/api/admin/ai-usage/policies",
        headers=bearer(admin_token),
        json={"scope": "user", "target_id": str(user.id), "request_limit": 5},
    )
    assert created.status_code == 201, created.text
    policy_id = created.json()["id"]
    body = {
        "requests": {"state": "blocked"},
        "tokens": {"state": "inherit"},
        "effective_from": (container.clock.now() - timedelta(hours=1)).isoformat(),
        "expires_at": (container.clock.now() + timedelta(days=7)).isoformat(),
    }
    bad = await client.post(
        f"/api/admin/ai-usage/policies/{policy_id}/overrides",
        headers=bearer(admin_token),
        json={**body, "requests": {"state": "unlimited", "value": 0}},
    )
    assert bad.status_code == 422
    forbidden = await client.post(
        f"/api/admin/ai-usage/policies/{policy_id}/overrides", headers=bearer(user_token), json=body
    )
    assert forbidden.status_code == 403
    response = await client.post(
        f"/api/admin/ai-usage/policies/{policy_id}/overrides",
        headers=bearer(admin_token),
        json=body,
    )
    assert response.status_code == 201, response.text
    override_id = response.json()["id"]
    mine = await client.get("/api/ai-usage/me", headers=bearer(user_token))
    [item] = [row for row in mine.json()["items"] if row["policy"]["id"] == policy_id]
    assert item["request_limit"] == 0 and item["policy"]["request_limit"] == 5
    assert item["override"]["id"] == override_id
    listing = await client.get(
        f"/api/admin/ai-usage/policies/{policy_id}/overrides", headers=bearer(admin_token)
    )
    assert [row["id"] for row in listing.json()["items"]] == [override_id]
    revoked = await client.delete(
        f"/api/admin/ai-usage/overrides/{override_id}", headers=bearer(admin_token)
    )
    assert revoked.status_code == 200 and revoked.json()["revoked_at"] is not None
    audit = await client.get("/api/admin/audit-log", headers=bearer(admin_token))
    actions = {row["action"] for row in audit.json()["items"]}
    assert {"ai_usage_override_created", "ai_usage_override_revoked"} <= actions
