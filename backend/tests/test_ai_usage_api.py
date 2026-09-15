"""HTTP contracts for AI usage policy administration and self-service summaries."""

from __future__ import annotations

from uuid import UUID

from ai_usage_helpers import accounting
from ase.domain.ai_usage import AiAttribution, AiCallOutcome
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)


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


async def _record_team_call(container, user_id, team_id, prompt, completion):
    ledger = accounting(container)
    batch = await ledger.reserve(
        AiAttribution.actor(user_id, team_id),
        profile_id=None,
        model="fixture-model",
        purpose="team-test",
        requested_tokens=50,
    )
    await ledger.finish(
        batch, AiCallOutcome.COMPLETED, prompt_tokens=prompt, completion_tokens=completion
    )


async def test_admin_outside_team_sees_team_policy_in_team_view_and_preview(client, admin, user):
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    team = await client.post("/api/teams", headers=bearer(user_token), json={"name": "Desk"})
    team_id = team.json()["id"]
    created = await client.post(
        "/api/admin/ai-usage/policies",
        headers=bearer(admin_token),
        json={"scope": "team", "target_id": team_id, "request_limit": 9},
    )
    assert created.status_code == 201, created.text
    view = await client.get(f"/api/teams/{team_id}/ai-usage", headers=bearer(admin_token))
    assert view.status_code == 200, view.text
    assert view.json()["view"] == "admin"
    assert [item["policy"]["scope"] for item in view.json()["items"]] == ["team"]
    preview = await client.get(
        f"/api/admin/ai-usage/preview?user_id={admin.id}&team_id={team_id}",
        headers=bearer(admin_token),
    )
    assert preview.status_code == 200, preview.text
    assert {item["policy"]["scope"] for item in preview.json()["items"]} == {"team"}
    system = await client.get(
        "/api/admin/ai-usage/preview?system=true", headers=bearer(admin_token)
    )
    assert system.status_code == 200 and system.json()["unknown_calls"] == 0


async def test_team_usage_view_depends_on_membership_role(client, container, admin, user):
    member = await create_user(container, email="member@example.com", password=USER_PASSWORD)
    outsider = await create_user(container, email="outsider@example.com", password=USER_PASSWORD)
    manager_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    team = await client.post("/api/teams", headers=bearer(manager_token), json={"name": "Ops"})
    team_id = team.json()["id"]
    added = await client.put(
        f"/api/teams/{team_id}/members",
        headers=bearer(manager_token),
        json={"email": "member@example.com"},
    )
    assert added.status_code == 200, added.text
    await _record_team_call(container, user.id, UUID(team_id), 10, 5)
    await _record_team_call(container, member.id, UUID(team_id), 3, 4)
    await _record_team_call(container, member.id, None, 100, 100)  # personal, not team usage

    manager = await client.get(f"/api/teams/{team_id}/ai-usage", headers=bearer(manager_token))
    body = manager.json()
    assert body["view"] == "manager"
    assert (body["team"]["used_requests"], body["team"]["used_tokens"]) == (2, 22)
    assert {row["display_name"]: row["observed"]["used_tokens"] for row in body["members"]} == {
        "User": 15,
        "Member": 7,
    }
    member_token = await login_token(client, "member@example.com", USER_PASSWORD)
    own = (await client.get(f"/api/teams/{team_id}/ai-usage", headers=bearer(member_token))).json()
    assert own["view"] == "member" and own["team"] is None and own["members"] is None
    assert (own["own"]["used_requests"], own["own"]["used_tokens"]) == (1, 7)
    outsider_token = await login_token(client, "outsider@example.com", USER_PASSWORD)
    hidden = await client.get(f"/api/teams/{team_id}/ai-usage", headers=bearer(outsider_token))
    assert hidden.status_code == 404
    assert outsider.id != member.id
    mine = (await client.get("/api/ai-usage/me", headers=bearer(member_token))).json()
    assert mine["items"] == [] and mine["observed"]["used_requests"] == 2
