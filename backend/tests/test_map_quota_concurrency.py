"""Concurrent saves share the database-backed administration guard and one quota."""

import asyncio

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.map_view_models import MapViewRow
from ase.application.research import map_views
from helpers import USER_PASSWORD, bearer, login_token
from test_report_team_scope import save_team_report


@pytest.fixture
def settings(settings, tmp_path):
    # Real separate SQLite connections, or the caller's explicitly selected test PG.
    if settings.database_url.startswith("sqlite"):
        return settings.model_copy(
            update={
                "database_url": f"sqlite+aiosqlite:///{tmp_path / 'concurrent-maps.db'}",
            }
        )
    return settings


async def test_two_concurrent_saves_cannot_both_claim_last_scope_slot(
    client,
    container,
    user,
    monkeypatch,
):
    monkeypatch.setattr(map_views, "MAX_SCOPE_VIEWS", 1)
    report = await save_team_report(container, user, None)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    body = {
        "report_id": str(report.id),
        "version_number": 1,
        "title": "Last slot",
        "state": {"camera": {"longitude": 0, "latitude": 0, "zoom": 2}},
    }
    results = await asyncio.gather(
        *(client.post("/api/map/views", headers=headers, json=body) for _ in range(2))
    )
    assert sorted(response.status_code for response in results) == [201, 422]
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(MapViewRow)) == 1
