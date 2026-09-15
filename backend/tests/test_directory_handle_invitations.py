"""Exact-username invitations reach hidden accounts without confirming that they exist."""

from __future__ import annotations

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)


async def _team_with_manager(
    client: AsyncClient, container: Container, admin: User
) -> tuple[str, dict[str, str]]:
    manager = await create_user(container, email="handles@example.com", password=USER_PASSWORD)
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post("/api/teams", json={"name": "Handle desk"}, headers=admin_headers)
    assert created.status_code == 201, created.text
    team_id = created.json()["id"]
    added = await client.put(
        f"/api/teams/{team_id}/members",
        headers=admin_headers,
        json={"email": manager.email, "role": "manager"},
    )
    assert added.status_code < 300, added.text
    return team_id, bearer(await login_token(client, manager.email, USER_PASSWORD))


async def _handle(client: AsyncClient, user: User, username: str, discoverable: bool) -> None:
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.patch(
        "/api/me/directory-profile",
        headers=headers,
        json={"username": username, "is_discoverable": discoverable},
    )
    assert response.status_code == 200, response.text


async def test_hidden_and_unknown_handles_receive_identical_responses(
    client: AsyncClient, container: Container, admin: User
) -> None:
    team_id, manager_headers = await _team_with_manager(client, container, admin)
    hidden = await create_user(container, email="hidden-target@example.com", password=USER_PASSWORD)
    await _handle(client, hidden, "hidden_target", discoverable=False)
    path = f"/api/teams/{team_id}/invitations/by-username"

    responses = [
        await client.post(path, headers=manager_headers, json={"username": name})
        for name in ("hidden_target", "nobody_here", "HIDDEN_TARGET", "admin", "bad name!")
    ]

    assert {response.status_code for response in responses} == {202}
    assert len({response.text for response in responses}) == 1
    assert set(responses[0].json()) == {"status", "message"}
    assert "hidden" not in responses[0].text.lower()

    pending = await client.get(f"/api/teams/{team_id}/invitations", headers=manager_headers)
    items = pending.json()["items"]
    # One invitation was delivered, and the duplicate submission did not create another.
    assert [item["recipient_id"] for item in items] == [str(hidden.id)]

    inbox = await client.get(
        "/api/me/team-invitations",
        headers=bearer(await login_token(client, hidden.email, USER_PASSWORD)),
    )
    assert inbox.json()["items"][0]["team_name"] == "Handle desk"

    # Broad directory search still does not reveal the hidden account.
    search = await client.get(
        "/api/directory/users", headers=manager_headers, params={"q": "hidden_target"}
    )
    assert search.json()["total"] == 0


async def test_self_and_administrator_handles_are_not_revealed(
    client: AsyncClient, container: Container, admin: User
) -> None:
    team_id, manager_headers = await _team_with_manager(client, container, admin)
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    await client.patch(
        "/api/me/directory-profile", headers=admin_headers, json={"username": "site_admin"}
    )
    path = f"/api/teams/{team_id}/invitations/by-username"

    await client.patch(
        "/api/me/directory-profile", headers=manager_headers, json={"username": "desk_manager"}
    )

    as_admin = await client.post(path, headers=manager_headers, json={"username": "site_admin"})
    as_self = await client.post(path, headers=manager_headers, json={"username": "desk_manager"})
    unknown = await client.post(path, headers=manager_headers, json={"username": "nobody"})
    assert as_admin.status_code == as_self.status_code == unknown.status_code == 202
    assert as_admin.json() == as_self.json() == unknown.json()
    pending = await client.get(f"/api/teams/{team_id}/invitations", headers=manager_headers)
    assert pending.json()["total"] == 0


async def test_handle_invitations_enforce_sender_authority_first(
    client: AsyncClient, container: Container, admin: User
) -> None:
    team_id, _manager_headers = await _team_with_manager(client, container, admin)
    outsider = await create_user(container, email="outsider@example.com", password=USER_PASSWORD)
    target = await create_user(container, email="target@example.com", password=USER_PASSWORD)
    await _handle(client, target, "real_target", discoverable=False)
    outsider_headers = bearer(await login_token(client, outsider.email, USER_PASSWORD))
    path = f"/api/teams/{team_id}/invitations/by-username"

    for username in ("real_target", "nobody_here"):
        denied = await client.post(path, headers=outsider_headers, json={"username": username})
        assert denied.status_code == 404
    assert (await client.post(path, json={"username": "real_target"})).status_code == 401
    extra = await client.post(
        path, headers=outsider_headers, json={"username": "real_target", "role": "manager"}
    )
    assert extra.status_code == 422


async def test_handle_submissions_are_rate_limited(
    client: AsyncClient, container: Container, admin: User
) -> None:
    team_id, manager_headers = await _team_with_manager(client, container, admin)
    path = f"/api/teams/{team_id}/invitations/by-username"
    statuses = [
        (
            await client.post(path, headers=manager_headers, json={"username": f"ghost_{n}"})
        ).status_code
        for n in range(21)
    ]
    assert statuses[:20] == [202] * 20
    assert statuses[20] == 429
