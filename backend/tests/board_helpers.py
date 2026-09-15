"""Shared set-up for team board and dashboard API tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient

from ase.container import Container
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)

MANAGER_EMAIL = "lead@example.com"
MANAGER_PASSWORD = "Harbour-Lights-Burn-77"


@dataclass(frozen=True, slots=True)
class BoardDesk:
    team_id: str
    admin: dict[str, str]
    manager: dict[str, str]
    user: dict[str, str]

    def posts(self, suffix: str = "") -> str:
        return f"/api/teams/{self.team_id}/board/posts{suffix}"


async def board_desk(client: AsyncClient, container: Container) -> BoardDesk:
    """An active team with an Administrator creator, a Manager and an ordinary Member."""
    await create_user(container, email=MANAGER_EMAIL, password=MANAGER_PASSWORD)
    admin = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post("/api/teams", json={"name": "Board desk"}, headers=admin)
    assert created.status_code == 201, created.text
    team_id = created.json()["id"]
    for email, role in ((USER_EMAIL, "member"), (MANAGER_EMAIL, "manager")):
        added = await client.put(
            f"/api/teams/{team_id}/members", json={"email": email, "role": role}, headers=admin
        )
        assert added.status_code == 200, added.text
    return BoardDesk(
        team_id,
        admin,
        bearer(await login_token(client, MANAGER_EMAIL, MANAGER_PASSWORD)),
        bearer(await login_token(client, USER_EMAIL, USER_PASSWORD)),
    )


async def post(
    client: AsyncClient, desk: BoardDesk, headers: dict[str, str], text: str, **extra: Any
) -> dict[str, Any]:
    response = await client.post(desk.posts(), json={"text": text, **extra}, headers=headers)
    assert response.status_code == 201, response.text
    payload: dict[str, Any] = response.json()
    return payload
