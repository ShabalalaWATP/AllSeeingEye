"""HTTP authorisation, validation and no-store contracts for research levels."""

import pytest

from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_allowance_and_administration_contract(client, admin, user):
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    user_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    me = await client.get("/api/research-usage/me", headers=user_headers)
    assert me.status_code == 200
    assert me.headers["cache-control"] == "no-store"
    assert me.json()["remaining"] == 4 and me.json()["revision"] == 0
    listed = await client.get("/api/admin/research-usage", headers=admin_headers)
    assert listed.status_code == 200 and listed.headers["cache-control"] == "no-store"
    assert [tier["limit"] for tier in listed.json()["tiers"]] == [4, 4, 13, 32, None]
    assert {row["user_id"] for row in listed.json()["items"]} == {str(user.id), str(admin.id)}
    for target in (user, admin):
        updated = await client.put(
            f"/api/admin/users/{target.id}/research-tier",
            headers=admin_headers,
            json={"tier": 4, "expected_revision": 0},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["tier"] == 4 and updated.json()["remaining"] == 32
        conflict = await client.put(
            f"/api/admin/users/{target.id}/research-tier",
            headers=admin_headers,
            json={"tier": 2, "expected_revision": 0},
        )
        assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "conflict"
    assert (await client.get("/api/admin/research-usage", headers=user_headers)).status_code == 403
    assert (
        await client.put(
            f"/api/admin/users/{user.id}/research-tier",
            headers=user_headers,
            json={"tier": 4, "expected_revision": 1},
        )
    ).status_code == 403
    assert (await client.get("/api/research-usage/me")).status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"tier": True, "expected_revision": 0},
        {"tier": 0, "expected_revision": 0},
        {"tier": 6, "expected_revision": 0},
        {"tier": "2", "expected_revision": 0},
        {"tier": 2.0, "expected_revision": 0},
        {"tier": 2, "expected_revision": -1},
        {"tier": 2, "expected_revision": True},
        {"tier": 2, "expected_revision": 0, "role": "admin"},
    ],
)
async def test_tier_input_is_strict(client, admin, body):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    result = await client.put(
        f"/api/admin/users/{admin.id}/research-tier", headers=headers, json=body
    )
    assert result.status_code == 422
