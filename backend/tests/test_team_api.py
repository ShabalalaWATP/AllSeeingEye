"""HTTP team contract, input bounds and scoped roster visibility."""

from uuid import uuid4

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import Role, User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)


async def test_team_http_lifecycle(client: AsyncClient, admin: User, user: User) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post(
        "/api/teams",
        json={"name": "Watch desk", "description": "Shared OSINT desk"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["description"] == "Shared OSINT desk"
    team_id = created.json()["id"]
    added = await client.put(
        f"/api/teams/{team_id}/members", json={"email": user.email}, headers=headers
    )
    assert added.status_code == 200 and added.json()["role"] == "member"
    user_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    listed = await client.get("/api/teams", headers=user_headers)
    assert listed.json()["items"][0]["id"] == team_id
    detail = await client.get(f"/api/teams/{team_id}", headers=user_headers)
    member = next(item for item in detail.json()["members"] if item["user_id"] == str(user.id))
    # Teams are self-service, so a roster never discloses login email addresses.
    assert user.email not in detail.text
    assert set(member) == {
        "user_id",
        "display_name",
        "username",
        "account_role",
        "is_active",
        "role",
        "joined_at",
    }
    assert member["username"] is None
    assert (
        await client.patch(f"/api/teams/{team_id}", json={"name": "Renamed"}, headers=user_headers)
    ).status_code == 403
    assert (await client.get(f"/api/teams/{uuid4()}", headers=user_headers)).status_code == 404
    assert (
        await client.patch(f"/api/teams/{team_id}", json={"is_active": False}, headers=headers)
    ).status_code == 200
    assert not (await client.get(f"/api/teams/{team_id}", headers=user_headers)).json()["team"][
        "is_active"
    ]
    assert (
        await client.patch(f"/api/teams/{team_id}", json={"is_active": True}, headers=headers)
    ).status_code == 200
    removed = await client.delete(f"/api/teams/{team_id}/members/{user.id}", headers=headers)
    assert removed.status_code == 204
    assert (await client.get(f"/api/teams/{team_id}", headers=user_headers)).status_code == 404


async def test_team_input_bounds_and_authentication(client: AsyncClient, admin: User) -> None:
    assert (await client.get("/api/teams")).status_code == 401
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    for body in ({"name": " "}, {"name": "x" * 121}, {"name": "Desk", "created_by": str(uuid4())}):
        assert (await client.post("/api/teams", json=body, headers=headers)).status_code == 422
    response = await client.post("/api/teams", json={"name": "Desk"}, headers=headers)
    team_id = response.json()["id"]
    for body in (
        {"email": "invalid"},
        {"email": "a@example.com", "role": "admin"},
        {"email": "a@example.com", "is_active": True},
    ):
        assert (
            await client.put(f"/api/teams/{team_id}/members", json=body, headers=headers)
        ).status_code == 422
    assert (
        await client.patch(f"/api/teams/{team_id}", json={}, headers=headers)
    ).status_code == 422


async def test_manager_has_no_account_directory_or_administrative_power(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    manager = await create_user(
        container, email="lead@example.com", password=USER_PASSWORD, role=Role.MANAGER
    )
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    team = await client.post("/api/teams", json={"name": "Led desk"}, headers=admin_headers)
    team_id = team.json()["id"]
    assert (
        await client.put(
            f"/api/teams/{team_id}/members",
            json={"email": manager.email, "role": "manager"},
            headers=admin_headers,
        )
    ).status_code == 200
    headers = bearer(await login_token(client, manager.email, USER_PASSWORD))
    assert (await client.get("/api/admin/users", headers=headers)).status_code == 403
    created_by_manager = await client.post("/api/teams", json={"name": "Own"}, headers=headers)
    assert created_by_manager.status_code == 201
    own_team_id = created_by_manager.json()["id"]
    inactive = await create_user(
        container, email="inactive-target@example.com", password=None, is_active=False
    )
    # Managers invite people. Direct add is refused identically for every target,
    # so the response cannot reveal whether an email exists or is an Administrator.
    responses = [
        await client.put(
            f"/api/teams/{team}/members", json={"email": email, "role": "manager"}, headers=headers
        )
        for team in (team_id, own_team_id)
        for email in (user.email, ADMIN_EMAIL, inactive.email, "nobody@example.com")
    ]
    assert {response.status_code for response in responses} == {403}
    assert len({response.json()["error"]["message"] for response in responses}) == 1
    assert (
        await client.put(
            f"/api/teams/{team_id}/members", json={"email": user.email}, headers=admin_headers
        )
    ).status_code == 200
    promoted = await client.patch(
        f"/api/teams/{team_id}/members/{user.id}", json={"role": "manager"}, headers=headers
    )
    assert promoted.status_code == 200 and promoted.json()["role"] == "manager"
    assert (
        await client.patch(
            f"/api/teams/{team_id}/members/{admin.id}", json={"role": "member"}, headers=headers
        )
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/teams/{own_team_id}/members/{uuid4()}", json={"role": "member"}, headers=headers
        )
    ).status_code == 404


async def test_user_can_create_and_leave_after_appointing_another_manager(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    second = await create_user(container, email="second-member@example.com", password=USER_PASSWORD)
    user_headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    created = await client.post(
        "/api/teams", json={"name": "Self-service desk"}, headers=user_headers
    )
    assert created.status_code == 201, created.text
    team_id = created.json()["id"]
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    assert (
        await client.put(
            f"/api/teams/{team_id}/members",
            json={"email": second.email},
            headers=admin_headers,
        )
    ).status_code == 200
    assert (
        await client.patch(
            f"/api/teams/{team_id}/members/{second.id}",
            json={"role": "manager"},
            headers=user_headers,
        )
    ).status_code == 200
    left = await client.post(f"/api/teams/{team_id}/leave", headers=user_headers)
    assert left.status_code == 204, left.text
    assert (await client.get(f"/api/teams/{team_id}", headers=user_headers)).status_code == 404


async def test_last_manager_leave_is_rejected_over_http(client: AsyncClient, user: User) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    created = await client.post("/api/teams", json={"name": "Protected desk"}, headers=headers)
    team_id = created.json()["id"]
    response = await client.post(f"/api/teams/{team_id}/leave", headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


async def test_admin_api_rejects_the_retired_global_manager_role(
    client: AsyncClient, admin: User, user: User
) -> None:
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    response = await client.patch(
        f"/api/admin/users/{user.id}", json={"role": "manager"}, headers=headers
    )
    assert response.status_code == 422
    assert (
        await client.patch(f"/api/admin/users/{user.id}", json={"role": "user"}, headers=headers)
    ).status_code == 200
