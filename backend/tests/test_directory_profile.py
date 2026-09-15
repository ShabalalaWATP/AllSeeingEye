"""Directory profiles are opt-in, bounded and separate from private preferences."""

import pytest
from httpx import AsyncClient

from ase.container import Container
from helpers import USER_PASSWORD, bearer, create_user, login_token


async def test_owner_can_read_and_update_directory_profile(
    client: AsyncClient, container: Container
) -> None:
    owner = await create_user(container, email="owner@example.com", password=USER_PASSWORD)
    headers = bearer(await login_token(client, owner.email, USER_PASSWORD))

    initial = await client.get("/api/me/directory-profile", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["is_discoverable"] is False
    assert initial.json()["username"] is None
    assert initial.json()["timezone"] is None
    assert "timezone" not in initial.json()["visible_fields"]

    updated = await client.patch(
        "/api/me/directory-profile",
        headers=headers,
        json={
            "username": "  OSINT_Lead ",
            "job_title": "Research analyst",
            "organisation": "Open Source Desk",
            "biography": "Tracks public reporting and primary sources.",
            "country": "gb",
            "languages": ["en", "ru", "en"],
            "expertise": ["Conflict", "conflict", "Maritime"],
            "timezone": "Europe/London",
            "is_discoverable": True,
            "visible_fields": ["organisation", "timezone"],
        },
    )
    assert updated.status_code == 200, updated.text
    result = updated.json()
    assert result["username"] == "osint_lead"
    assert result["country"] == "GB"
    assert result["languages"] == ["en", "ru"]
    assert result["expertise"] == ["Conflict", "Maritime"]
    assert result["timezone"] == "Europe/London"
    assert result["visible_fields"] == ["organisation", "timezone"]
    assert result["avatar_url"] is None
    assert result["revision"] == 2

    private = await client.patch(
        "/api/me/directory-profile",
        headers=headers,
        json={"visible_fields": ["organisation"], "expected_revision": result["revision"]},
    )
    assert private.status_code == 200
    # Visibility governs other accounts; the owner still sees the saved value.
    assert private.json()["timezone"] == "Europe/London"
    assert private.json()["visible_fields"] == ["organisation"]


async def test_directory_search_only_returns_active_opted_in_profiles(
    client: AsyncClient, container: Container
) -> None:
    owner = await create_user(container, email="visible@example.com", password=USER_PASSWORD)
    hidden = await create_user(container, email="hidden@example.com", password=USER_PASSWORD)
    inactive = await create_user(
        container, email="inactive@example.com", password=USER_PASSWORD, is_active=False
    )
    owner_headers = bearer(await login_token(client, owner.email, USER_PASSWORD))
    hidden_headers = bearer(await login_token(client, hidden.email, USER_PASSWORD))

    visible = await client.patch(
        "/api/me/directory-profile",
        headers=owner_headers,
        json={
            "username": "visible_user",
            "organisation": "Signal Research",
            "is_discoverable": True,
        },
    )
    assert visible.status_code == 200, visible.text
    await client.patch(
        "/api/me/directory-profile",
        headers=hidden_headers,
        json={"username": "hidden_user", "organisation": "Signal Research"},
    )

    by_name = await client.get("/api/directory/users", headers=hidden_headers, params={"q": "Vis"})
    assert by_name.status_code == 200, by_name.text
    assert by_name.json()["total"] == 1
    item = by_name.json()["items"][0]
    assert item["username"] == "visible_user"
    assert item["display_name"] == "Visible"
    assert "email" not in item
    assert str(inactive.id) not in {row["user_id"] for row in by_name.json()["items"]}

    by_org = await client.get(
        "/api/directory/users", headers=hidden_headers, params={"q": "Signal", "limit": 1}
    )
    assert by_org.status_code == 200
    assert [row["username"] for row in by_org.json()["items"]] == ["visible_user"]


async def test_username_is_unique_and_updates_are_revision_checked(
    client: AsyncClient, container: Container
) -> None:
    first = await create_user(container, email="first@example.com", password=USER_PASSWORD)
    second = await create_user(container, email="second@example.com", password=USER_PASSWORD)
    first_headers = bearer(await login_token(client, first.email, USER_PASSWORD))
    second_headers = bearer(await login_token(client, second.email, USER_PASSWORD))

    created = await client.patch(
        "/api/me/directory-profile",
        headers=first_headers,
        json={"username": "shared_name"},
    )
    assert created.status_code == 200

    duplicate = await client.patch(
        "/api/me/directory-profile",
        headers=second_headers,
        json={"username": "SHARED_NAME"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "username_taken"

    stale = await client.patch(
        "/api/me/directory-profile",
        headers=first_headers,
        json={"biography": "stale", "expected_revision": 1},
    )
    assert stale.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": "ab"},
        {"username": "admin"},
        {"is_discoverable": True},
        {"country": "GBR"},
        {"languages": ["en"] * 9},
        {"expertise": ["x"] * 11},
        {"timezone": "Mars/Base"},
        {"visible_fields": ["email"]},
        {"visible_fields": None},
        {"show_timezone": True},
    ],
)
async def test_invalid_directory_profile_changes_are_rejected(
    client: AsyncClient, container: Container, payload: dict[str, object]
) -> None:
    owner = await create_user(container, email="invalid@example.com", password=USER_PASSWORD)
    headers = bearer(await login_token(client, owner.email, USER_PASSWORD))
    result = await client.patch("/api/me/directory-profile", headers=headers, json=payload)
    assert result.status_code == 422, result.text


async def test_directory_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/me/directory-profile")).status_code == 401
    assert (await client.get("/api/directory/users", params={"q": "ab"})).status_code == 401
