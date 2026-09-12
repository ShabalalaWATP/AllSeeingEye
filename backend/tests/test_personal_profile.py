"""Private preferences persist per identity without permitting account escalation."""

from dataclasses import replace

import pytest
from httpx import AsyncClient

from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.errors import Unauthenticated
from ase.domain.research import ResearchMode
from ase.domain.users import Role, User
from helpers import ADMIN_PASSWORD, USER_PASSWORD, bearer, create_user, login_token


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("mode", list(ResearchMode))
async def test_every_role_can_save_own_profile(
    client: AsyncClient,
    container: Container,
    role: Role,
    mode: ResearchMode,
) -> None:
    user = await create_user(
        container, email="profile@example.com", password=USER_PASSWORD, role=role
    )
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    default = await client.get("/api/me/profile", headers=headers)
    assert default.status_code == 200
    assert default.headers["cache-control"] == "no-store"
    assert default.json()["research_window_days"] == 3
    assert default.json()["appearance_theme"] == "obsidian"
    assert default.json()["reduced_motion"] is False
    changes = {
        "display_name": "  Analyst One  ",
        "timezone": "Europe/London",
        "date_format": "iso",
        "research_mode": mode.value,
        "research_languages": ["en", "fr", "en"],
        "research_country": "GB",
        "research_window_days": 14,
        "report_language": "fr",
        "report_style": "briefing",
        "export_format": "docx",
        "appearance_theme": "slate",
        "reduced_motion": True,
    }
    response = await client.patch("/api/me/profile", headers=headers, json=changes)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["display_name"] == "Analyst One"
    assert result["research_languages"] == ["en", "fr"]
    assert result["appearance_theme"] == "slate"
    assert result["reduced_motion"] is True
    assert (await client.get("/api/me/profile", headers=headers)).json() == result
    me = (await client.get("/api/me", headers=headers)).json()
    assert me["display_name"] == "Analyst One" and me["role"] == role.value
    cleared = await client.patch(
        "/api/me/profile", headers=headers, json={"research_country": None}
    )
    assert cleared.json()["research_country"] is None
    assert cleared.json()["report_language"] == "fr"


async def test_profiles_are_private_even_from_other_admins(
    client: AsyncClient,
    container: Container,
    user: User,
    admin: User,
) -> None:
    owner = bearer(await login_token(client, user.email, USER_PASSWORD))
    await client.patch(
        "/api/me/profile",
        headers=owner,
        json={"research_languages": ["uk"], "appearance_theme": "light", "reduced_motion": True},
    )
    other = await create_user(container, email="other@example.com", password=USER_PASSWORD)
    theirs = bearer(await login_token(client, other.email, USER_PASSWORD))
    result = await client.get("/api/me/profile", headers=theirs)
    assert result.json()["research_languages"] == ["en"]
    assert result.json()["appearance_theme"] == "obsidian"
    assert result.json()["reduced_motion"] is False
    assert (await client.get(f"/api/me/profile/{user.id}", headers=theirs)).status_code == 404
    admin_headers = bearer(await login_token(client, admin.email, ADMIN_PASSWORD))
    assert (await client.get("/api/me/profile", headers=admin_headers)).json()[
        "research_languages"
    ] == ["en"]
    assert (
        await client.get(f"/api/me/profile/{user.id}", headers=admin_headers)
    ).status_code == 404


@pytest.mark.parametrize(
    "changes",
    [
        {"role": "admin"},
        {"email": "changed@example.com"},
        {"user_id": "other"},
        {"display_name": " "},
        {"display_name": "bad\nname"},
        {"timezone": "Mars/Base"},
        {"timezone": "../Europe/London"},
        {"research_languages": []},
        {"research_languages": ["English"]},
        {"research_languages": ["en"] * 9},
        {"research_country": "GBR"},
        {"research_window_days": 90},
        {"research_window_days": True},
        {"report_language": "xx"},
        {"report_style": "propaganda"},
        {"export_format": "exe"},
        {"date_format": None},
        {"display_name": None},
        {"research_mode": None},
        {"appearance_theme": "arbitrary-css"},
        {"appearance_theme": None},
        {"reduced_motion": "yes"},
        {"reduced_motion": 1},
        {"reduced_motion": None},
    ],
)
async def test_invalid_profile_changes_are_rejected(
    client: AsyncClient,
    user: User,
    changes: dict[str, object],
) -> None:
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.patch("/api/me/profile", headers=headers, json=changes)
    assert response.status_code == 422, response.text


async def test_anonymous_profile_access_is_rejected(client: AsyncClient) -> None:
    assert (await client.get("/api/me/profile")).status_code == 401
    assert (await client.patch("/api/me/profile", json={"display_name": "x"})).status_code == 401


async def test_stale_identity_cannot_read_or_overwrite_profile(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    claims = container.issuer.verify(await login_token(client, user.email, USER_PASSWORD))
    async with container.session_factory() as session:
        with pytest.raises(Unauthenticated):
            await container.profile(session).get(replace(claims, security_version=99))
        with pytest.raises(Unauthenticated):
            await container.profile(session).update(
                replace(claims, security_version=99),
                {"display_name": "stale"},
                RequestContext(ip="127.0.0.1"),
            )


async def test_revoked_family_cannot_read_or_save_after_prior_authentication(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    token = await login_token(client, user.email, USER_PASSWORD)
    claims = container.issuer.verify(token)
    async with container.session_factory() as session:
        # Represents a request whose dependency accepted these claims before the
        # administrator/user selected this family for revocation.
        assert (await container.profile(session).get(claims)).display_name == user.display_name
        repositories = container.repositories(session)
        await repositories.users.lock_administration()
        await repositories.users.lock_by_id(user.id)
        await repositories.refresh_tokens.revoke_family(claims.family_id, container.clock.now())
        await repositories.uow.commit()
    async with container.session_factory() as session:
        with pytest.raises(Unauthenticated):
            await container.profile(session).update(
                claims, {"display_name": "revoked write"}, RequestContext()
            )
        with pytest.raises(Unauthenticated):
            await container.profile(session).get(claims)
        current = await container.repositories(session).users.get_by_id(user.id)
        assert current and current.display_name == user.display_name
        assert current.security_version == claims.security_version
    assert (
        await client.patch(
            "/api/me/profile", headers=bearer(token), json={"display_name": "revoked write"}
        )
    ).status_code == 401
