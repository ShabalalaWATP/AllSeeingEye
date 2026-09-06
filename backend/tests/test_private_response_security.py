"""Private operational responses reject caching and late export authorisation loss."""

from dataclasses import replace

import pytest
from httpx import AsyncClient

from ase.application.reports import exports
from ase.container import Container
from ase.domain.users import User
from helpers import USER_PASSWORD, bearer, login_token
from report_search_helpers import add_report


@pytest.mark.parametrize(
    "path",
    [
        "/api/teams",
        "/api/direction/plans",
        "/api/direction/aois",
        "/api/reports",
        "/api/report-search",
        "/api/warning/indicators",
        "/api/warning/alerts",
        "/api/schedules",
        "/api/trackers/social",
    ],
)
async def test_private_api_responses_are_never_cacheable(
    client: AsyncClient, user: User, path: str
) -> None:
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.get(path, headers=headers)
    assert "no-store" in response.headers.get("cache-control", "")


async def test_export_rechecks_access_after_renderer_finishes(
    client: AsyncClient, container: Container, user: User, monkeypatch
) -> None:
    async with container.session_factory() as session:
        record, _ = await add_report(container, session, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))

    async def render_then_revoke(*_args):
        async with container.session_factory() as session:
            await container.repositories(session).users.save(replace(user, is_active=False))
            await session.commit()
        return b"PRIVATE EXPORT CONTENT"

    monkeypatch.setattr(exports.asyncio, "to_thread", render_then_revoke)
    response = await client.get(f"/api/reports/{record.id}/export/pdf", headers=headers)
    assert response.status_code == 401
    assert b"PRIVATE EXPORT CONTENT" not in response.content
