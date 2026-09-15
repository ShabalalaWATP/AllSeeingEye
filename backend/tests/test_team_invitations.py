"""Invitation lifecycle and directory privacy boundaries."""

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


async def _directory_user(client: AsyncClient, user: User) -> dict[str, str]:
    token = await login_token(client, user.email, USER_PASSWORD)
    response = await client.patch(
        "/api/me/directory-profile",
        headers=bearer(token),
        json={"username": "field_operator", "is_discoverable": True},
    )
    assert response.status_code == 200, response.text
    return bearer(token)


async def test_admin_can_invite_and_user_can_accept(
    client: AsyncClient, admin: User, user: User
) -> None:
    user_headers = await _directory_user(client, user)
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post(
        "/api/teams", json={"name": "Invitation desk"}, headers=admin_headers
    )
    assert created.status_code == 201
    team_id = created.json()["id"]

    sent = await client.post(
        f"/api/teams/{team_id}/invitations",
        headers=admin_headers,
        json={"recipient_id": str(user.id), "note": "Welcome to the desk"},
    )
    assert sent.status_code == 201, sent.text
    invitation = sent.json()
    assert invitation["status"] == "pending"
    assert invitation["recipient_display_name"] == user.display_name

    inbox = await client.get("/api/me/team-invitations", headers=user_headers)
    assert inbox.status_code == 200
    assert inbox.json()["items"][0]["team_name"] == "Invitation desk"
    accepted = await client.post(
        f"/api/me/team-invitations/{invitation['id']}/accept",
        headers=user_headers,
        json={"expected_revision": invitation["revision"]},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    roster = await client.get(f"/api/teams/{team_id}", headers=user_headers)
    assert roster.status_code == 200
    assert any(member["user_id"] == str(user.id) for member in roster.json()["members"])


async def test_manager_cannot_invite_non_discoverable_or_administrator(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    manager = await create_user(
        container, email="invite-manager@example.com", password=USER_PASSWORD
    )
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post("/api/teams", json={"name": "Private desk"}, headers=admin_headers)
    team_id = created.json()["id"]
    await client.put(
        f"/api/teams/{team_id}/members",
        headers=admin_headers,
        json={"email": manager.email, "role": "manager"},
    )
    manager_headers = bearer(await login_token(client, manager.email, USER_PASSWORD))
    hidden = await client.post(
        f"/api/teams/{team_id}/invitations",
        headers=manager_headers,
        json={"recipient_id": str(user.id)},
    )
    assert hidden.status_code == 422
    assert "directory" in hidden.json()["error"]["message"].lower()
