"""Both FIRMS delivery families expose their legacy parent opt-out consistently."""

import pytest

from ase.adapters.feeds.firms import sensor_spec
from ase.adapters.feeds.firms_public import public_sensor_spec
from ase.adapters.feeds.firms_sensors import FIRMS_SENSORS
from ase.adapters.persistence.source_controls import SqlSourceAdmission
from feeds_helpers import FakeConnector
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_events_api import app  # noqa: F401
from test_source_controls import disable


@pytest.mark.parametrize("factory", [sensor_spec, public_sensor_spec])
async def test_family_parent_controls_sql_admission_admin_listing_and_activation(
    client, container, admin, factory
):
    parent, child = [factory(sensor) for sensor in FIRMS_SENSORS]
    container.scheduler._connectors.update(
        {spec.id: FakeConnector(spec) for spec in (parent, child)}
    )
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    headers = bearer(token)
    await disable(container, admin, parent.id)
    admission = SqlSourceAdmission(container.session_factory)
    assert not await admission.enabled(child.id)
    assert (await admission.enabled_many((parent.id, child.id))) == {
        parent.id: False,
        child.id: False,
    }
    rows = (await client.get("/api/admin/sources", headers=headers)).json()["items"]
    row = next(row for row in rows if row["id"] == child.id)
    assert row["enabled"] is False
    blocked = await client.patch(
        f"/api/admin/sources/{child.id}/activation", headers=headers, json={"enabled": True}
    )
    assert blocked.status_code == 422
    assert parent.name in blocked.text and "research variant" not in blocked.text
    assert (
        await client.patch(
            f"/api/admin/sources/{parent.id}/activation", headers=headers, json={"enabled": True}
        )
    ).status_code == 204
    assert await admission.enabled(child.id)
    assert (
        await client.patch(
            f"/api/admin/sources/{child.id}/activation", headers=headers, json={"enabled": False}
        )
    ).status_code == 204
    assert await admission.enabled(parent.id)
    assert not await admission.enabled(child.id)


@pytest.mark.parametrize("factory", [sensor_spec, public_sensor_spec])
async def test_environment_parent_optout_is_visible_and_cannot_be_bypassed(
    client, container, admin, factory, monkeypatch
):
    parent, child = [factory(sensor) for sensor in FIRMS_SENSORS]
    container.scheduler._connectors.update(
        {spec.id: FakeConnector(spec) for spec in (parent, child)}
    )
    monkeypatch.setattr(
        container,
        "settings",
        container.settings.model_copy(update={"feeds_disabled": parent.id}),
    )
    monkeypatch.setattr(
        container, "source_admission", SqlSourceAdmission(container.session_factory, (parent.id,))
    )
    assert not await container.source_admission.enabled(child.id)
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    headers = bearer(token)
    rows = (await client.get("/api/admin/sources", headers=headers)).json()["items"]
    row = next(row for row in rows if row["id"] == child.id)
    assert row["enabled"] is False and row["environment_disabled"] is True
    response = await client.patch(
        f"/api/admin/sources/{child.id}/activation", headers=headers, json={"enabled": True}
    )
    assert response.status_code == 422
