"""Synthetic teams and scoped direction requests, independent of operator data."""

from dataclasses import dataclass

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


@dataclass(frozen=True)
class DirectionActors:
    admin: dict[str, str]
    owner: dict[str, str]
    member: dict[str, str]
    manager: dict[str, str]
    outsider: dict[str, str]
    member_user: User
    manager_user: User
    team: str
    other_team: str


async def direction_actors(
    client: AsyncClient, container: Container, owner: User
) -> DirectionActors:
    member = await create_user(container, email="member@example.com", password=USER_PASSWORD)
    manager = await create_user(
        container, email="manager@example.com", password=USER_PASSWORD, role=Role.MANAGER
    )
    outsider = await create_user(container, email="outsider@example.com", password=USER_PASSWORD)
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    teams = []
    for name in ("North", "South"):
        response = await client.post("/api/teams", json={"name": name}, headers=admin_headers)
        assert response.status_code == 201, response.text
        teams.append(response.json()["id"])
    for target, role in ((owner, "member"), (member, "member"), (manager, "manager")):
        response = await client.put(
            f"/api/teams/{teams[0]}/members",
            json={"email": target.email, "role": role},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
    return DirectionActors(
        admin_headers,
        bearer(await login_token(client, USER_EMAIL, USER_PASSWORD)),
        bearer(await login_token(client, member.email, USER_PASSWORD)),
        bearer(await login_token(client, manager.email, USER_PASSWORD)),
        bearer(await login_token(client, outsider.email, USER_PASSWORD)),
        member,
        manager,
        teams[0],
        teams[1],
    )


def area(name: str = "Area", team: str | None = None) -> dict[str, object]:
    return {"name": name, "kind": "countries", "countries": ["UA"], "team_id": team}


def plan(name: str = "Plan", team: str | None = None, aoi: str | None = None) -> dict[str, object]:
    return {
        "name": name,
        "team_id": team,
        "aoi_id": aoi,
        "pirs": [
            {
                "text": "What changed?",
                "sirs": [{"text": "Border developments", "keywords": ["border"]}],
            }
        ],
    }
