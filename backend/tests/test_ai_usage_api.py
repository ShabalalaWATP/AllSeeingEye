"""HTTP contracts for AI usage policy administration and self-service summaries."""

from __future__ import annotations

from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_policy_and_self_usage_api_expose_limits_without_secrets(client, admin, user):
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    body = {
        "scope": "global",
        "period": "day",
        "request_limit": 3,
        "token_limit": 1000,
        "enabled": True,
    }
    created = await client.post(
        "/api/admin/ai-usage/policies", headers=bearer(admin_token), json=body
    )
    assert created.status_code == 201, created.text
    policy_id = created.json()["id"]
    listing = await client.get("/api/admin/ai-usage/policies", headers=bearer(admin_token))
    assert listing.status_code == 200 and listing.json()[0]["id"] == policy_id
    summary = await client.get("/api/ai-usage/me", headers=bearer(user_token))
    assert summary.status_code == 200
    assert summary.json()["items"][0]["remaining_requests"] == 3
    assert (
        await client.get("/api/admin/ai-usage/policies", headers=bearer(user_token))
    ).status_code == 403
    disabled = await client.delete(
        f"/api/admin/ai-usage/policies/{policy_id}", headers=bearer(admin_token)
    )
    assert disabled.status_code == 204


async def test_admin_can_preview_effective_account_and_team_allowances(client, admin, user):
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    global_policy = await client.post(
        "/api/admin/ai-usage/policies",
        headers=bearer(admin_token),
        json={
            "scope": "global",
            "period": "day",
            "request_limit": 12,
            "token_limit": 1000,
            "enabled": True,
        },
    )
    assert global_policy.status_code == 201, global_policy.text
    team_response = await client.post(
        "/api/teams", headers=bearer(user_token), json={"name": "Preview desk"}
    )
    assert team_response.status_code == 201, team_response.text
    team_id = team_response.json()["id"]
    team_policy = await client.post(
        "/api/admin/ai-usage/policies",
        headers=bearer(admin_token),
        json={
            "scope": "team",
            "target_id": team_id,
            "period": "day",
            "request_limit": 4,
            "token_limit": 300,
            "enabled": True,
        },
    )
    assert team_policy.status_code == 201, team_policy.text
    personal = await client.get(
        f"/api/admin/ai-usage/preview?user_id={user.id}", headers=bearer(admin_token)
    )
    assert personal.status_code == 200
    assert {item["policy"]["scope"] for item in personal.json()["items"]} == {"global"}
    team = await client.get(
        f"/api/admin/ai-usage/preview?user_id={user.id}&team_id={team_id}",
        headers=bearer(admin_token),
    )
    assert team.status_code == 200
    assert {item["policy"]["scope"] for item in team.json()["items"]} == {"global", "team"}
    assert (
        await client.get(
            f"/api/admin/ai-usage/preview?user_id={user.id}", headers=bearer(user_token)
        )
    ).status_code == 403
