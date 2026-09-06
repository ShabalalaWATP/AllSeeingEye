"""Private library metadata never widens report access or changes frozen content."""

from dataclasses import replace
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from ase.adapters.persistence.library_models import ResearchLibraryRow, ResearchLibraryTagRow
from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.errors import Unauthenticated
from ase.domain.research_library import LibraryPreference
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, FakeClock, bearer, login_token
from team_helpers import CONTEXT, team_service
from test_report_team_scope import save_team_report, team_for


async def test_private_preferences_are_not_visible_to_other_users_or_admins(
    client: AsyncClient,
    container: Container,
    user: User,
    admin: User,
) -> None:
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    path = f"/api/me/library/{report.id}"
    before = (await client.get(f"/api/reports/{report.id}", headers=headers)).json()
    saved = await client.put(
        path,
        headers=headers,
        json={"favourite": True, "tags": [" Defence ", "UK"], "note": "private note"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["tags"] == ["defence", "uk"]
    assert saved.headers["cache-control"] == "no-store"
    assert (await client.get(path, headers=admin_headers)).json()["note"] is None
    assert (await client.get("/api/me/library", headers=admin_headers)).json()["total"] == 0
    assert (await client.get(path, headers=headers)).json()["note"] == "private note"
    after = (await client.get(f"/api/reports/{report.id}", headers=headers)).json()
    assert before == after
    assert (await client.get("/api/me/library", headers=headers)).json()["total"] == 1


async def test_library_entries_do_not_grant_parent_access(
    client: AsyncClient,
    container: Container,
    user: User,
    admin: User,
) -> None:
    report = await save_team_report(container, admin, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    path = f"/api/me/library/{report.id}"
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (await client.put(path, headers=headers, json={"favourite": True})).status_code == 404
    assert (await client.delete(path, headers=headers)).status_code == 404
    assert (await client.get("/api/me/library", headers=headers)).json()["total"] == 0


async def test_membership_removal_filters_before_count_and_limit(
    client: AsyncClient,
    container: Container,
    user: User,
    admin: User,
    clock: FakeClock,
) -> None:
    team = await team_for(container, admin, user)
    own = await save_team_report(container, user, None)
    shared = await save_team_report(container, admin, team.id)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for report in (own, shared):
        clock.advance(timedelta(seconds=1))
        result = await client.put(
            f"/api/me/library/{report.id}",
            headers=headers,
            json={"favourite": True, "tags": ["same"]},
        )
        assert result.status_code == 200, result.text
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    page = (
        await client.get("/api/me/library?limit=1&tag=SAME&favourite_only=true", headers=headers)
    ).json()
    assert page["total"] == 1
    assert [item["report"]["id"] for item in page["items"]] == [str(own.id)]
    assert (await client.get(f"/api/me/library/{shared.id}", headers=headers)).status_code == 404
    assert (await client.get("/api/me/library?tag=unmatched", headers=headers)).json()["total"] == 0


async def test_removed_entry_leaves_report_and_report_deletion_cascades_annotations(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    path = f"/api/me/library/{report.id}"
    assert (await client.put(path, headers=headers, json={"tags": ["saved"]})).status_code == 200
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.get(f"/api/reports/{report.id}", headers=headers)).status_code == 200
    assert (await client.put(path, headers=headers, json={"tags": ["saved"]})).status_code == 200
    assert (await client.delete(f"/api/reports/{report.id}", headers=headers)).status_code == 204
    async with container.session_factory() as session:
        for model in (ResearchLibraryRow, ResearchLibraryTagRow):
            assert await session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize(
    "body",
    [
        {"tags": ["x"] * 13},
        {"tags": ["x", "X"]},
        {"tags": ["x" * 41]},
        {"tags": [""]},
        {"tags": ["bad\nvalue"]},
        {"note": "n" * 1001},
        {"note": "a\0b"},
        {"favourite": "true"},
        {"team_id": None},
        {"user_id": "other"},
    ],
)
async def test_bounds_and_scope_mutation_fields_rejected(
    client: AsyncClient,
    container: Container,
    user: User,
    body,
) -> None:
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (
        await client.put(f"/api/me/library/{report.id}", headers=headers, json=body)
    ).status_code == 422


async def test_revoked_family_rechecked_inside_library_application(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    report = await save_team_report(container, user, None)
    token = await login_token(client, user.email, USER_PASSWORD)
    claims = container.issuer.verify(token)
    async with container.session_factory() as session:
        await container.repositories(session).refresh_tokens.revoke_family(
            claims.family_id, container.clock.now()
        )
        await session.commit()
    async with container.session_factory() as session:
        service = container.research_library(session)
        for operation in (
            lambda: service.list(claims),
            lambda: service.get(claims, report.id),
            lambda: service.save(claims, report.id, LibraryPreference(True), RequestContext()),
            lambda: service.remove(claims, report.id, RequestContext()),
            lambda: service.list(replace(claims, security_version=999)),
        ):
            with pytest.raises(Unauthenticated):
                await operation()


async def test_anonymous_library_and_invalid_pagination(client: AsyncClient, user: User) -> None:
    assert (await client.get("/api/me/library")).status_code == 401
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for query in ("limit=101", "offset=-1", "offset=10001", "tag=", "tag=" + "x" * 41):
        assert (await client.get("/api/me/library?" + query, headers=headers)).status_code == 422
