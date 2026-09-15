"""Per-field directory visibility, response-key privacy and exact-handle resolution."""

from __future__ import annotations

from dataclasses import replace

from httpx import AsyncClient

from ase.application.account.directory_profile import resolve_exact_handle
from ase.container import Container
from ase.domain.users import User
from helpers import USER_PASSWORD, bearer, create_user, login_token

FULL_PROFILE = {
    "job_title": "Maritime analyst",
    "organisation": "Harbour Watch",
    "biography": "Follows port calls.",
    "country": "NO",
    "languages": ["en", "nb"],
    "expertise": ["Shipping"],
    "timezone": "Europe/Oslo",
    "is_discoverable": True,
}
DIRECTORY_RESULT_KEYS = {
    "user_id",
    "username",
    "display_name",
    "avatar_url",
    "job_title",
    "organisation",
    "biography",
    "country",
    "languages",
    "expertise",
    "timezone",
}


async def _publish(
    client: AsyncClient, user: User, username: str, **changes: object
) -> dict[str, str]:
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.patch(
        "/api/me/directory-profile",
        headers=headers,
        json={**FULL_PROFILE, "username": username, **changes},
    )
    assert response.status_code == 200, response.text
    return headers


async def test_search_returns_only_owner_selected_fields(
    client: AsyncClient, container: Container
) -> None:
    owner = await create_user(container, email="selective@example.com", password=USER_PASSWORD)
    viewer = await create_user(container, email="viewer@example.com", password=USER_PASSWORD)
    await _publish(client, owner, "selective", visible_fields=["organisation", "country"])
    viewer_headers = bearer(await login_token(client, viewer.email, USER_PASSWORD))

    result = await client.get(
        "/api/directory/users", headers=viewer_headers, params={"q": "selective"}
    )
    assert result.status_code == 200, result.text
    item = result.json()["items"][0]
    assert item["organisation"] == "Harbour Watch"
    assert item["country"] == "NO"
    assert item["job_title"] is None
    assert item["biography"] is None
    assert item["languages"] == []
    assert item["expertise"] == []
    assert item["timezone"] is None
    for hidden in ("Maritime analyst", "Follows port calls", "Shipping", "Europe/Oslo", "nb"):
        assert hidden not in result.text


async def test_timezone_is_private_by_default_and_opt_in(
    client: AsyncClient, container: Container
) -> None:
    owner = await create_user(container, email="zone@example.com", password=USER_PASSWORD)
    viewer = await create_user(container, email="zoneviewer@example.com", password=USER_PASSWORD)
    owner_headers = await _publish(client, owner, "zone_owner")
    viewer_headers = bearer(await login_token(client, viewer.email, USER_PASSWORD))

    default = await client.get(
        "/api/directory/users", headers=viewer_headers, params={"q": "zone_owner"}
    )
    item = default.json()["items"][0]
    assert item["timezone"] is None
    assert item["job_title"] == "Maritime analyst"

    opted = await client.patch(
        "/api/me/directory-profile",
        headers=owner_headers,
        json={"visible_fields": ["timezone"]},
    )
    assert opted.status_code == 200
    shown = await client.get(
        "/api/directory/users", headers=viewer_headers, params={"q": "zone_owner"}
    )
    item = shown.json()["items"][0]
    assert item["timezone"] == "Europe/Oslo"
    assert item["job_title"] is None


async def test_hidden_organisation_is_not_searchable(
    client: AsyncClient, container: Container
) -> None:
    owner = await create_user(container, email="orgpriv@example.com", password=USER_PASSWORD)
    viewer = await create_user(container, email="orgview@example.com", password=USER_PASSWORD)
    await _publish(client, owner, "org_private", visible_fields=["job_title"])
    viewer_headers = bearer(await login_token(client, viewer.email, USER_PASSWORD))

    by_org = await client.get(
        "/api/directory/users", headers=viewer_headers, params={"q": "Harbour"}
    )
    assert by_org.status_code == 200
    assert by_org.json()["total"] == 0
    by_name = await client.get(
        "/api/directory/users", headers=viewer_headers, params={"q": "org_private"}
    )
    assert by_name.json()["total"] == 1


async def test_directory_results_never_expose_account_security_data(
    client: AsyncClient, container: Container
) -> None:
    owner = await create_user(container, email="keys@example.com", password=USER_PASSWORD)
    viewer = await create_user(container, email="keysviewer@example.com", password=USER_PASSWORD)
    await _publish(client, owner, "key_check", visible_fields=list(FULL_PROFILE)[:7])
    viewer_headers = bearer(await login_token(client, viewer.email, USER_PASSWORD))

    result = await client.get(
        "/api/directory/users", headers=viewer_headers, params={"q": "key_check"}
    )
    assert result.status_code == 200
    body = result.json()
    assert set(body) == {"items", "total", "offset", "limit", "next_offset"}
    assert set(body["items"][0]) == DIRECTORY_RESULT_KEYS
    lowered = result.text.lower()
    for forbidden in ("keys@example.com", "email", "mfa", "totp", "session", "security_version"):
        assert forbidden not in lowered
    assert "is_discoverable" not in body["items"][0]
    assert "visible_fields" not in body["items"][0]


async def test_exact_handle_resolves_non_discoverable_active_accounts_only(
    client: AsyncClient, container: Container
) -> None:
    hidden = await create_user(container, email="hiddenhandle@example.com", password=USER_PASSWORD)
    leaver = await create_user(container, email="leaver@example.com", password=USER_PASSWORD)
    await _publish(client, hidden, "quiet_handle", is_discoverable=False)
    await _publish(client, leaver, "former_handle")
    async with container.session_factory() as session:
        repos = container.repositories(session)
        user = await repos.users.get_by_id(leaver.id)
        assert user is not None
        await repos.users.save(replace(user, is_active=False))
        await repos.uow.commit()

    async with container.session_factory() as session:
        repos = container.repositories(session)
        profiles, users = repos.directory_profiles, repos.users
        assert await resolve_exact_handle(profiles, users, "quiet_handle") == hidden.id
        assert await resolve_exact_handle(profiles, users, "  QUIET_Handle ") == hidden.id
        assert await resolve_exact_handle(profiles, users, "quiet_hand") is None
        assert await resolve_exact_handle(profiles, users, "quiet%") is None
        assert await resolve_exact_handle(profiles, users, "admin") is None
        assert await resolve_exact_handle(profiles, users, "") is None
        assert await resolve_exact_handle(profiles, users, "former_handle") is None
