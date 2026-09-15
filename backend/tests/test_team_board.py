"""Team board permissions, replies and revision safety."""

from httpx import AsyncClient

from ase.container import Container
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_team_board_lifecycle_and_membership_boundary(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    admin_headers = bearer(admin_token)
    user_headers = bearer(user_token)

    created = await client.post("/api/teams", json={"name": "Board desk"}, headers=admin_headers)
    assert created.status_code == 201, created.text
    team_id = created.json()["id"]
    added = await client.put(
        f"/api/teams/{team_id}/members",
        json={"email": "user@example.com"},
        headers=admin_headers,
    )
    assert added.status_code == 200, added.text

    post = await client.post(
        f"/api/teams/{team_id}/board/posts",
        json={"text": "Handover: review the satellite imagery."},
        headers=user_headers,
    )
    assert post.status_code == 201, post.text
    payload = post.json()
    assert payload["author_name"] == "User"

    reply = await client.post(
        f"/api/teams/{team_id}/board/posts",
        json={"text": "I will take that review.", "parent_id": payload["id"]},
        headers=user_headers,
    )
    assert reply.status_code == 201, reply.text

    listed = await client.get(f"/api/teams/{team_id}/board/posts", headers=user_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 2

    edited = await client.patch(
        f"/api/teams/{team_id}/board/posts/{payload['id']}",
        json={"text": "Updated handover.", "expected_revision": payload["revision"]},
        headers=user_headers,
    )
    assert edited.status_code == 200
    assert edited.json()["text"] == "Updated handover."

    pinned = await client.post(
        f"/api/teams/{team_id}/board/posts/{payload['id']}/pin",
        json={"pinned": True, "expected_revision": edited.json()["revision"]},
        headers=admin_headers,
    )
    assert pinned.status_code == 200 and pinned.json()["is_pinned"] is True

    stale = await client.patch(
        f"/api/teams/{team_id}/board/posts/{payload['id']}",
        json={"text": "Stale edit.", "expected_revision": 1},
        headers=user_headers,
    )
    assert stale.status_code == 422

    removed = await client.delete(
        f"/api/teams/{team_id}/board/posts/{payload['id']}?expected_revision={pinned.json()['revision']}",
        headers=user_headers,
    )
    assert removed.status_code == 204


async def test_team_board_requires_joined_member(
    client: AsyncClient, admin: object, user: object
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post(
        "/api/teams", json={"name": "Private board"}, headers=bearer(admin_token)
    )
    team_id = created.json()["id"]
    response = await client.get(f"/api/teams/{team_id}/board/posts", headers=bearer(user_token))
    assert response.status_code == 404
