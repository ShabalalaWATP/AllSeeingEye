"""The API reports licence refusals without presenting them as a healthy connection."""

import pytest
from httpx import AsyncClient

from ase.domain.source_licences import LICENCE_UNAVAILABLE
from ase.domain.users import User
from ase.infrastructure.settings import Settings
from feeds_helpers import FakeConnector, make_spec
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token

FORBIDDEN = "cloudflare_radar_outages"
PERMISSION = "usgs_earthquakes"


@pytest.fixture(params=[(False, ""), (True, ""), (True, PERMISSION)])
def settings(settings: Settings, request: pytest.FixtureRequest) -> Settings:
    commercial_use, acknowledgements = request.param
    return settings.model_copy(
        update={
            "commercial_use": commercial_use,
            "source_licence_acknowledgements": acknowledgements,
        }
    )


@pytest.fixture
def feed_connectors() -> list[FakeConnector]:
    # Known catalogue identities with a local fake, never a live provider request.
    return [FakeConnector(make_spec(source_id)) for source_id in (FORBIDDEN, PERMISSION)]


async def test_admin_licence_metadata_and_effective_admission(
    client: AsyncClient, admin: User, settings: Settings
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.get("/api/admin/sources", headers=bearer(token))
    assert response.status_code == 200
    rows = {item["id"]: item for item in response.json()["items"]}
    for source_id in (FORBIDDEN, PERMISSION):
        allowed = not settings.commercial_use or (
            source_id == PERMISSION and source_id in settings.acknowledged_source_licences
        )
        licence = rows[source_id]["licence"]
        assert licence["available"] is allowed
        assert licence["attribution_required"] is True
        assert licence["licence_ref"] == f"docs/SOURCE_LICENCES.md#source-{source_id}"
        assert rows[source_id]["collection_mode"] == "scheduled"
        assert rows[source_id]["enabled"] is allowed
        if not allowed:
            assert rows[source_id]["test_available"] is False
        assert licence["acknowledged"] is (source_id in settings.acknowledged_source_licences)
    assert rows[FORBIDDEN]["licence"]["commercial_use"] == "forbidden"
    assert rows[PERMISSION]["licence"]["commercial_use"] == "licence_required"


async def test_user_inventory_keeps_honest_source_and_asset_unavailability(
    client: AsyncClient, user: User, settings: Settings
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    response = await client.get("/api/sources", headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    rows = {item["id"]: item for item in response.json()["items"]}
    assets = {item["id"]: item for item in response.json()["assets"]}
    for source_id in (FORBIDDEN, PERMISSION):
        blocked = settings.commercial_use and (
            source_id == FORBIDDEN or source_id not in settings.acknowledged_source_licences
        )
        connection = rows[source_id]["connection"]
        assert (connection["state"] == "disabled_by_licence") is blocked
        if blocked:
            assert connection["detail"] == LICENCE_UNAVAILABLE
            assert connection["health"] is None
            assert connection["enabled"] is False
            assert connection["active"] is False
    eox = assets["map:eox_s2cloudless"]
    assert (eox["state"] == "disabled_by_licence") is settings.commercial_use
    if settings.commercial_use:
        assert eox["detail"] == LICENCE_UNAVAILABLE
        assert eox["records"] is None
    # Operator-only controls remain protected when the source itself is blocked.
    assert (await client.get("/api/admin/sources", headers=headers)).status_code == 403
