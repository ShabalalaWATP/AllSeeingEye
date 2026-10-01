"""The read-only source catalogue is open to every role; source administration is not."""

import pytest
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

MANAGER_EMAIL = "catalogue-manager@example.com"
FIRMS = "/api/admin/sources/firms_viirs_noaa20/connection"


# Every administrative source route, with a well-formed body so only authorisation decides.
def admin_routes(source_id: str) -> tuple[tuple[str, str, dict[str, object] | None], ...]:
    return (
        ("GET", "/api/admin/sources", None),
        ("PATCH", f"/api/admin/sources/{source_id}/activation", {"enabled": False}),
        ("POST", f"/api/admin/sources/{source_id}/test", None),
        ("POST", f"/api/admin/sources/{source_id}/reset", None),
        ("GET", FIRMS, None),
        ("PUT", f"{FIRMS}/draft", {"expected_revision": 0, "api_key": "x" * 32}),
        ("POST", f"{FIRMS}/test", {"expected_revision": 0}),
        ("POST", f"{FIRMS}/confirm", {"expected_revision": 0, "test_generation": 1}),
        ("DELETE", FIRMS, {"expected_revision": 0}),
    )


async def role_headers(client: AsyncClient, container: Container) -> dict[str, dict[str, str]]:
    await create_user(container, email=MANAGER_EMAIL, password=USER_PASSWORD, role=Role.MANAGER)
    return {
        "user": bearer(await login_token(client, USER_EMAIL, USER_PASSWORD)),
        "manager": bearer(await login_token(client, MANAGER_EMAIL, USER_PASSWORD)),
        "admin": bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)),
    }


@pytest.mark.parametrize("path", ["/api/sources", "/api/sources/connections"])
async def test_catalogue_reads_require_sign_in(client: AsyncClient, path: str) -> None:
    assert (await client.get(path)).status_code == 401


async def test_every_role_reads_the_same_catalogue_contract(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    headers = await role_headers(client, container)
    shapes: dict[str, tuple[set[str], set[str]]] = {}
    for role, auth in headers.items():
        sources = await client.get("/api/sources", headers=auth)
        connections = await client.get("/api/sources/connections", headers=auth)
        assert sources.status_code == 200, (role, sources.text)
        assert connections.status_code == 200, (role, connections.text)
        assert sources.headers["cache-control"] == "private, no-store"
        assert connections.headers["cache-control"] == "private, no-store"
        items = sources.json()["items"]
        assert items
        # Grades always arrive with their recorded basis and limitations.
        assert all(item["rating"]["basis"] and item["rating"]["limitations"] for item in items)
        shapes[role] = (
            set().union(*(item.keys() for item in items)),
            set().union(*(row.keys() for row in connections.json()["items"])),
        )
    # Administrators get no extra operational fields through the shared read contract.
    assert shapes["user"] == shapes["manager"] == shapes["admin"]
    source_fields, connection_fields = shapes["user"]
    assert not {"url", "error", "last_error", "credentials", "test_available"} & source_fields
    assert connection_fields == {"id", "name", "purpose", "state", "requirement", "detail"}


@pytest.mark.parametrize("role", ["user", "manager"])
async def test_non_admins_cannot_reach_source_administration(
    client: AsyncClient, container: Container, admin: User, user: User, role: str
) -> None:
    auth = (await role_headers(client, container))[role]
    before = (await client.get("/api/sources", headers=auth)).json()["items"]
    target = next(item["id"] for item in before if item["connection"]["enabled"])
    for method, path, body in admin_routes(target):
        response = await client.request(method, path, headers=auth, json=body)
        assert response.status_code == 403, (role, method, path, response.text)
    # The refused activation left the source switched on for everyone.
    after = (await client.get("/api/sources", headers=auth)).json()["items"]
    assert next(item for item in after if item["id"] == target)["connection"]["enabled"] is True
