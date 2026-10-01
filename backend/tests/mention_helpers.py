"""A board desk whose members have directory handles, plus an outsider, for mention tests."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

from httpx import AsyncClient

from ase.container import Container
from board_helpers import BoardDesk, board_desk
from helpers import USER_PASSWORD, bearer, create_user, login_token

BELL = "/api/bell"


@dataclass(frozen=True, slots=True)
class MentionDesk:
    desk: BoardDesk
    outsider: dict[str, str]
    peer: dict[str, str]
    peer_id: str


async def set_handle(client: AsyncClient, headers: dict[str, str], username: str) -> None:
    response = await client.patch(
        "/api/me/directory-profile", json={"username": username}, headers=headers
    )
    assert response.status_code == 200, response.text


async def mention_desk(client: AsyncClient, container: Container) -> MentionDesk:
    """Admin, Manager (desk_lead) and Member (analyst) on one team; an outsider elsewhere."""
    desk = await board_desk(client, container)
    outsider = await create_user(container, email="outside@example.com", password=USER_PASSWORD)
    peer = await create_user(container, email="peer@example.com", password=USER_PASSWORD)
    added = await client.put(
        f"/api/teams/{desk.team_id}/members",
        json={"email": peer.email, "role": "member"},
        headers=desk.admin,
    )
    assert added.status_code == 200, added.text
    outsider_headers = bearer(await login_token(client, outsider.email, USER_PASSWORD))
    peer_headers = bearer(await login_token(client, peer.email, USER_PASSWORD))
    await set_handle(client, desk.user, "analyst")
    await set_handle(client, desk.manager, "desk_lead")
    await set_handle(client, desk.admin, "site_admin")
    await set_handle(client, outsider_headers, "outsider_one")
    await set_handle(client, peer_headers, "peer_one")
    return MentionDesk(desk, outsider_headers, peer_headers, str(peer.id))


async def mentions(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.get(BELL, headers=headers)
    assert response.status_code == 200, response.text
    section: dict[str, Any] = response.json()["mentions"]
    return section


async def deactivate(container: Container, user_id: str) -> None:
    async with container.session_factory() as session:
        repos = container.repositories(session)
        user = await repos.users.get_by_id(UUID(user_id))
        assert user is not None
        await repos.users.save(replace(user, is_active=False))
        await repos.uow.commit()
