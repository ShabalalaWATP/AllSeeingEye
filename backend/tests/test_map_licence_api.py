"""Direct authenticated routes cannot override commercial deployment policy."""

import pytest

from ase.domain.source_licences import LICENCE_UNAVAILABLE
from helpers import USER_PASSWORD, bearer, login_token
from test_map_image_package_api import image_request, saved_view


@pytest.fixture
def settings(settings):
    settings.commercial_use = True
    return settings


@pytest.mark.parametrize(
    "path",
    [
        "/api/tiles/os/Road_3857/7/63/42.png",
        "/api/reference?kind=aircraft&keys=abc123",
        "/api/figures",
        "/api/conflicts/ukraine/reference",
        "/api/conflicts/ukraine/images/not-real.jpg",
        "/api/conflicts/ukraine",
        "/api/conflicts/ukraine/digest",
    ],
)
async def test_direct_restricted_asset_returns_licence_reason(client, user, path):
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.get(path, headers=headers)
    assert response.status_code == 403, response.text
    assert LICENCE_UNAVAILABLE in response.text


async def test_eox_saved_map_remains_readable_but_licensed_assertion_cannot_export(
    client, container, user
):
    path, headers, saved = await saved_view(client, container, user, basemap="satellite")
    response = await client.post(
        path,
        headers=headers,
        json={
            **image_request(),
            "use_basis": "licensed",
            "permitted_use": "I have permission",
        },
    )
    assert response.status_code == 403, response.text
    assert LICENCE_UNAVAILABLE in response.text
    current = await client.get(
        f"/api/map/views/{saved['view']['id']}/revisions/{saved['revision']['id']}", headers=headers
    )
    assert current.status_code == 200
    assert current.json()["revision"]["state"]["basemap"] == "satellite"


async def test_camera_catalogue_reports_policy_and_no_media(client, user):
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.get("/api/cameras?provider=tfl", headers=headers)
    assert response.status_code == 200
    assert response.json()["cameras"] == []
    provider = next(row for row in response.json()["providers"] if row["id"] == "tfl")
    assert provider["status"] == "licence_blocked"
    assert provider["message"] == LICENCE_UNAVAILABLE


async def test_capabilities_exposes_policy_separately_from_configuration(client, user):
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.get("/api/capabilities", headers=headers)
    assert response.status_code == 200
    policy = response.json()
    assert policy["commercial_use"] is True
    assert policy["source_licences"]["map:eox_s2cloudless"]["available"] is False
    assert policy["source_licences"]["map:openfreemap"]["available"] is True
    assert policy["source_licences"]["camera:tfl"]["available"] is False
