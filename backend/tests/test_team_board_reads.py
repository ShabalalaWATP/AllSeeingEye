"""Per-membership board read cursors and unread counts."""

from datetime import timedelta

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from board_helpers import BoardDesk, board_desk, post


def _tick(container: Container) -> None:
    container.clock.advance(timedelta(seconds=5))  # type: ignore[attr-defined]


async def _unread(client: AsyncClient, desk: BoardDesk, headers: dict[str, str]) -> int:
    response = await client.get(desk.posts(), headers=headers)
    assert response.status_code == 200, response.text
    value: int = response.json()["unread_count"]
    return value


async def _mark(client: AsyncClient, desk: BoardDesk, headers: dict[str, str], post_id: str) -> int:
    response = await client.post(
        f"/api/teams/{desk.team_id}/board/read",
        json={"last_seen_post_id": post_id},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    value: int = response.json()["unread_count"]
    return value


async def test_unread_counts_other_peoples_posts_after_the_cursor(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    desk = await board_desk(client, container)
    mine = await post(client, desk, desk.user, "My own note.")
    _tick(container)
    first = await post(client, desk, desk.manager, "Manager update.")
    _tick(container)
    await post(client, desk, desk.admin, "Admin reply.", parent_id=first["id"])
    assert await _unread(client, desk, desk.user) == 2

    assert await _mark(client, desk, desk.user, first["id"]) == 1
    _tick(container)
    latest = await post(client, desk, desk.manager, "Another update.")
    assert await _unread(client, desk, desk.user) == 2
    assert await _mark(client, desk, desk.user, latest["id"]) == 0
    # Marking an older post never moves the cursor backwards.
    assert await _mark(client, desk, desk.user, mine["id"]) == 0

    # A removed post no longer counts as unread for anyone.
    _tick(container)
    hidden = await post(client, desk, desk.manager, "Wrong team.")
    assert await _unread(client, desk, desk.user) == 1
    removed = await client.delete(
        desk.posts(f"/{hidden['id']}?expected_revision=1"), headers=desk.manager
    )
    assert removed.status_code == 204
    assert await _unread(client, desk, desk.user) == 0


async def test_cursor_from_a_removed_membership_is_ignored_after_rejoining(
    client: AsyncClient, container: Container, admin: object, user: User
) -> None:
    desk = await board_desk(client, container)
    first = await post(client, desk, desk.manager, "Before removal.")
    assert await _mark(client, desk, desk.user, first["id"]) == 0

    removed = await client.delete(
        f"/api/teams/{desk.team_id}/members/{user.id}", headers=desk.admin
    )
    assert removed.status_code == 204, removed.text
    assert (await client.get(desk.posts(), headers=desk.user)).status_code == 404

    _tick(container)
    readded = await client.put(
        f"/api/teams/{desk.team_id}/members",
        json={"email": user.email, "role": "member"},
        headers=desk.admin,
    )
    assert readded.status_code == 200, readded.text
    assert await _unread(client, desk, desk.user) == 1


async def test_read_cursor_rejects_posts_from_another_team(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    desk = await board_desk(client, container)
    other = await client.post("/api/teams", json={"name": "Other desk"}, headers=desk.admin)
    assert other.status_code == 201
    foreign = await client.post(
        f"/api/teams/{other.json()['id']}/board/posts",
        json={"text": "Elsewhere."},
        headers=desk.admin,
    )
    assert foreign.status_code == 201
    response = await client.post(
        f"/api/teams/{desk.team_id}/board/read",
        json={"last_seen_post_id": foreign.json()["id"]},
        headers=desk.user,
    )
    assert response.status_code == 404
