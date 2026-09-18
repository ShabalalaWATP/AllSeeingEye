"""Atomic assignment matrix edits reuse tested proofs and exact audience revisions."""

from uuid import uuid4

import pytest

from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)
from test_llm import FakeGateway
from test_llm_connections import DRAFT, ROOT, draft, proof

WORKSPACE = f"{ROOT}/workspace"


def model_change(profile, receipt, *, scope="global", target=None, revision=None):
    return {
        "scope": scope,
        "target_id": target,
        "model": {
            "profile_id": profile["id"],
            "expected_profile_revision": receipt["revision"],
            "tested_config_hash": receipt["tested_config_hash"],
            "expected_binding_revision": revision,
        },
    }


def allowance_change(preset, *, scope="global", target=None, policy=None):
    return {
        "scope": scope,
        "target_id": target,
        "allowance": {
            "preset": preset,
            "expected_policy_id": policy["id"] if policy else None,
            "expected_policy_revision": policy["revision"] if policy else None,
        },
    }


async def apply(client, headers, *changes):
    return await client.put(WORKSPACE, headers=headers, json={"changes": list(changes)})


async def setup_models(client, container):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    first = await draft(client, headers, "Luna")
    second = await draft(client, headers, "Replacement")
    return (
        headers,
        first,
        await proof(client, headers, first),
        second,
        await proof(client, headers, second),
    )


async def test_batch_move_user_preserves_other_users_team_and_global(
    client, container, admin, user
):
    headers, first, receipt, second, next_receipt = await setup_models(client, container)
    other = await create_user(container, email="other@example.com", password=USER_PASSWORD)
    team = await client.post("/api/teams", headers=headers, json={"name": "Operations"})
    team_id = team.json()["id"]
    initial = await apply(
        client,
        headers,
        model_change(first, receipt, scope="user", target=str(user.id)),
        model_change(first, receipt, scope="team", target=team_id),
        model_change(first, receipt, scope="user", target=str(other.id)),
        model_change(first, receipt),  # Global is deliberately last in the request.
    )
    assert initial.status_code == 200, initial.text
    original = initial.json()["connections"]
    user_binding = next(item for item in original if item["user_id"] == str(user.id))
    change = model_change(
        second, next_receipt, scope="user", target=str(user.id), revision=user_binding["revision"]
    )
    change["allowance"] = allowance_change("light")["allowance"]
    changed = await apply(client, headers, change)
    assert changed.status_code == 200, changed.text
    current = changed.json()["connections"]
    assert len(current) == 4
    assert (
        next(item for item in current if item["user_id"] == str(user.id))["profile_id"]
        == second["id"]
    )
    assert [item for item in current if item["user_id"] != str(user.id)] == [
        item for item in original if item["user_id"] != str(user.id)
    ]
    assert changed.json()["policies"][0]["request_limit"] == 50
    team_binding = next(item for item in current if item["team_id"] == team_id)
    removed = await apply(
        client,
        headers,
        {
            "scope": "team",
            "target_id": team_id,
            "model": {
                "profile_id": None,
                "expected_binding_revision": team_binding["revision"],
            },
            "allowance": allowance_change("inherit")["allowance"],
        },
    )
    assert removed.status_code == 200
    assert removed.json()["connections"] == [item for item in current if not item["team_id"]]
    assert removed.json()["policies"] == changed.json()["policies"]


@pytest.mark.parametrize(
    "failure", ["proof", "profile_revision", "binding_revision", "policy_revision"]
)
async def test_late_failure_rolls_back_models_limits_and_audit(
    client, container, admin, user, failure
):
    headers, first, receipt, second, next_receipt = await setup_models(client, container)
    initial = await apply(client, headers, model_change(first, receipt))
    before = initial.json()["connections"]
    global_revision = before[0]["revision"]
    new_global = model_change(second, next_receipt, revision=global_revision)
    new_global["allowance"] = allowance_change("standard")["allowance"]
    invalid = model_change(second, next_receipt, scope="user", target=str(user.id))
    if failure == "proof":
        invalid["model"]["tested_config_hash"] = "0" * 64
    elif failure == "profile_revision":
        invalid["model"]["expected_profile_revision"] += 1
    elif failure == "binding_revision":
        invalid["model"]["expected_binding_revision"] = global_revision
    else:
        invalid["allowance"] = {
            "preset": "power",
            "expected_policy_id": str(uuid4()),
            "expected_policy_revision": 1,
        }
    async with container.session_factory() as session:
        audit_before = await container.repositories(session).audit.list_before(None, 100)
    result = await apply(client, headers, new_global, invalid)
    assert result.status_code == 422, result.text
    assert (await client.get(f"{ROOT}/connections", headers=headers)).json()["items"] == before
    assert (await client.get("/api/admin/ai-usage/policies", headers=headers)).json() == []
    profiles = (await client.get(f"{ROOT}/profiles", headers=headers)).json()["items"]
    assert not next(item for item in profiles if item["id"] == second["id"])["enabled"]
    async with container.session_factory() as session:
        assert await container.repositories(session).audit.list_before(None, 100) == audit_before


async def test_removal_has_exact_revision_and_global_cannot_be_removed(
    client, container, admin, user
):
    headers, first, receipt, _, _ = await setup_models(client, container)
    initial = await apply(
        client,
        headers,
        model_change(first, receipt),
        model_change(first, receipt, scope="user", target=str(user.id)),
    )
    binding = next(item for item in initial.json()["connections"] if item["user_id"])
    removal = {
        "scope": "user",
        "target_id": str(user.id),
        "model": {"profile_id": None, "expected_binding_revision": binding["revision"]},
    }
    removed = await apply(client, headers, removal)
    assert removed.status_code == 200 and len(removed.json()["connections"]) == 1
    assert (await apply(client, headers, removal)).status_code == 404
    removal["scope"], removal["target_id"] = "global", None
    assert (await apply(client, headers, removal)).status_code == 422


@pytest.mark.parametrize(
    "target_type", ["missing_user", "missing_team", "inactive_user", "inactive_team"]
)
async def test_allowance_only_edits_require_current_active_target(
    client, container, admin, user, target_type
):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    scope = "user" if target_type.endswith("user") else "team"
    target = str(uuid4())
    if target_type == "inactive_user":
        async with container.session_factory() as session:
            user.is_active = False
            await container.repositories(session).users.save(user)
            await session.commit()
        target = str(user.id)
    elif target_type == "inactive_team":
        team = await client.post("/api/teams", headers=headers, json={"name": "Archived"})
        target = team.json()["id"]
        await client.patch(f"/api/teams/{target}", headers=headers, json={"is_active": False})
    result = await apply(client, headers, allowance_change("light", scope=scope, target=target))
    assert result.status_code == (404 if target_type.startswith("missing") else 422)
    assert (await client.get("/api/admin/ai-usage/policies", headers=headers)).json() == []


@pytest.mark.parametrize(
    "changes",
    [
        [],
        [allowance_change("light")] * 101,
        [allowance_change("light")] * 2,
        [{"scope": "user", "allowance": {"preset": "light"}}],
        [{"scope": "global", "target_id": str(uuid4()), "allowance": {"preset": "light"}}],
        [{"scope": "global"}],
        [{"scope": "global", "model": {"profile_id": str(uuid4())}}],
        [{"scope": "global", "allowance": {"preset": "light", "expected_policy_revision": 1}}],
    ],
)
async def test_workspace_rejects_invalid_shapes(client, admin, changes):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    assert (await apply(client, headers, *changes)).status_code == 422


async def test_workspace_requires_authenticated_administrator(client, admin, user):
    changes = [allowance_change("blocked")]
    assert (await apply(client, {}, *changes)).status_code == 401
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await apply(client, headers, *changes)).status_code == 403


async def test_incomplete_roles_and_failed_test_cannot_be_assigned(client, container, admin):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    container.llm = FakeGateway()
    created = await client.post(
        f"{ROOT}/profiles", headers=headers, json={**DRAFT, "roles": ["assessment"]}
    )
    profile = created.json()
    receipt = await proof(client, headers, profile)
    assert (await apply(client, headers, model_change(profile, receipt))).status_code == 422
    edited = await client.put(f"{ROOT}/profiles/{profile['id']}", headers=headers, json=DRAFT)
    assert edited.status_code == 200
    receipt = await proof(client, headers, edited.json())
    container.llm = FakeGateway(content='{"ok":false}')
    await client.post(f"{ROOT}/profiles/{profile['id']}/test", headers=headers)
    assert (await apply(client, headers, model_change(profile, receipt))).status_code == 422
