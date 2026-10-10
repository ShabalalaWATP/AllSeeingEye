"""Licence refusals must not masquerade as administrator switches or missing keys."""

from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.radar_attack_trends import RadarAttackSnapshot
from ase.domain.source_licences import LICENCE_UNAVAILABLE
from feeds_helpers import FakeConnector, make_spec
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_cyber_api import disable


@pytest.fixture(params=[False, True])
def settings(settings, request):
    return settings.model_copy(update={"commercial_use": request.param})


@pytest.fixture
def feed_connectors():
    return [FakeConnector(make_spec("acled_events")), FakeConnector(make_spec("gdelt_events"))]


async def test_conflict_coverage_distinguishes_licence_and_admin_refusals(
    client, container, user, settings
):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.get("/api/trackers/conflict-sources", headers=headers)
    assert response.status_code == 200
    rows = {row["id"]: row for row in response.json()["items"]}
    if settings.commercial_use:
        for source_id in ("acled_events", "reliefweb_reports"):
            assert rows[source_id]["status"] == "not_configured"
            assert LICENCE_UNAVAILABLE in rows[source_id]["detail"]
            assert "administrator" not in rows[source_id]["detail"]
    else:
        assert rows["acled_events"]["status"] == "waiting"
    assert rows["gdelt_events"]["status"] == "waiting"
    await disable(container, "acled_events", user.id)
    response = await client.get("/api/trackers/conflict-sources", headers=headers)
    row = next(row for row in response.json()["items"] if row["id"] == "acled_events")
    expected = LICENCE_UNAVAILABLE if settings.commercial_use else "disabled by an administrator"
    assert expected in row["detail"]


async def test_radar_distinguishes_licence_refusal_without_reading_or_releasing_data(
    client, container, user, settings, monkeypatch
):
    reader = AsyncMock(return_value=RadarAttackSnapshot("ready", container.clock.now(), ()))
    monkeypatch.setattr(container.radar_attack_trends, "read", reader)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.get("/api/cyber/radar-attacks", headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    if settings.commercial_use:
        assert response.json()["status"] == "disabled_by_licence"
        assert response.json()["fetched_at"] is None
        assert response.json()["layers"] == []
        reader.assert_not_awaited()
    else:
        assert response.json()["status"] == "ready"
        reader.assert_awaited_once()
    await disable(container, "cloudflare_radar_attack_trends", user.id)
    response = await client.get("/api/cyber/radar-attacks", headers=headers)
    expected = "disabled_by_licence" if settings.commercial_use else "disabled"
    assert response.json()["status"] == expected
    assert response.json()["fetched_at"] is None
    assert response.json()["layers"] == []
