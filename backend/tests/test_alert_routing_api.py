"""External routing requires scope ownership and export authority, never just team readership."""

from uuid import UUID

import pytest
from sqlalchemy import select

from alert_routing_helpers import destination, rule, save_route
from ase.adapters.persistence.alert_routing_models import AlertWebhookDestinationRow
from ase.adapters.persistence.models import AuditLogRow
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, create_user, login_token


async def test_defaults_and_encrypted_redacted_destination(client, container, user, monkeypatch):
    headers, rule_id = await rule(client, user)
    path = f"/api/warning/indicators/{rule_id}/notifications"
    initial = (await client.get(path, headers=headers)).json()
    assert initial["email_enabled"] is False and initial["webhook_id"] is None
    assert initial["revision"] == 0 and initial["can_manage"]
    target = await destination(client, headers, monkeypatch)
    async with container.session_factory() as session:
        row = await session.get(AlertWebhookDestinationRow, UUID(target))
        assert row is not None and "secret-hook" not in row.url_encrypted
        assert (
            container.cipher.decrypt(row.url_encrypted) == "https://alerts.example.com/secret-hook"
        )
    listed = await client.get("/api/warning/webhook-destinations", headers=headers)
    assert "secret-hook" not in listed.text and "url" not in listed.text
    saved = await save_route(client, headers, rule_id, email=False, webhook=target)
    assert saved["revision"] == 1
    stale = await client.put(
        path, headers=headers, json={"email_enabled": True, "expected_revision": 0}
    )
    assert stale.status_code == 409
    assert (
        await client.delete(f"/api/warning/webhook-destinations/{target}", headers=headers)
    ).status_code == 204
    # Removing the destination clears the route that named it and advances its revision.
    cleared = (await client.get(path, headers=headers)).json()
    assert cleared["webhook_id"] is None and cleared["revision"] == 2
    invalid = await client.put(
        path, headers=headers, json={"webhook_id": target, "expected_revision": 2}
    )
    assert invalid.status_code == 422
    async with container.session_factory() as session:
        audits = list(
            await session.scalars(select(AuditLogRow).where(AuditLogRow.actor_user_id == user.id))
        )
        actions = {row.action for row in audits}
        assert {
            "alert_destination_registered",
            "alert_routing_updated",
            "alert_destination_removed",
        } <= actions
        assert "secret-hook" not in repr([(row.subject, row.details) for row in audits])


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://127.0.0.1/private",
        "https://169.254.169.254/latest",
        "https://[::1]/",
        "https://user:password@example.com/",
    ],
)
async def test_destination_registration_rejects_unsafe_urls(client, user, url):
    headers, _ = await rule(client, user)
    response = await client.post(
        "/api/warning/webhook-destinations", headers=headers, json={"name": "Unsafe", "url": url}
    )
    assert response.status_code == 422
    assert "password" not in response.text and url not in response.text


async def test_personal_destinations_cannot_cross_owners(client, container, user, monkeypatch):
    first_headers, _ = await rule(client, user)
    target = await destination(client, first_headers, monkeypatch)
    other = await create_user(container, email="other-routing@example.com", password=USER_PASSWORD)
    headers, other_rule = await rule(client, other)
    response = await client.put(
        f"/api/warning/indicators/{other_rule}/notifications",
        headers=headers,
        json={"webhook_id": target, "expected_revision": 0},
    )
    assert response.status_code in {404, 422}
    assert (await client.get("/api/warning/webhook-destinations", headers=headers)).json()[
        "items"
    ] == []
    assert (
        await client.delete(f"/api/warning/webhook-destinations/{target}", headers=headers)
    ).status_code == 404


async def test_member_rule_creator_cannot_export_team_alerts(
    client, container, admin, user, monkeypatch
):
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post(
        "/api/teams", headers=admin_headers, json={"name": "Restricted desk"}
    )
    team = created.json()["id"]
    added = await client.put(
        f"/api/teams/{team}/members",
        headers=admin_headers,
        json={"email": user.email, "role": "member"},
    )
    assert added.status_code == 200
    headers, rule_id = await rule(client, user, team_id=team)
    route_path = f"/api/warning/indicators/{rule_id}/notifications"
    assert (await client.get(route_path, headers=headers)).json()["can_manage"] is False
    assert (
        await client.put(
            route_path, headers=headers, json={"email_enabled": True, "expected_revision": 0}
        )
    ).status_code == 403
    assert (
        await client.get(
            "/api/warning/webhook-destinations", headers=headers, params={"team_id": team}
        )
    ).status_code == 403
    personal = await destination(client, headers, monkeypatch)
    scoped = await destination(client, admin_headers, monkeypatch, team_id=team)
    response = await client.put(
        route_path, headers=admin_headers, json={"webhook_id": personal, "expected_revision": 0}
    )
    assert response.status_code == 422
    assert (await save_route(client, admin_headers, rule_id, webhook=scoped))[
        "webhook_id"
    ] == scoped


async def test_copy_disclosure_is_truthful_without_revealing_installation_url(
    client, container, user
):
    headers, _ = await rule(client, user)
    path = "/api/warning/notification-capabilities"
    assert (await client.get(path, headers=headers)).json()["installation_copy_enabled"] is False
    container.settings.alert_webhook_url = "https://example.com/private-secret"
    response = await client.get(path, headers=headers)
    assert response.json()["installation_copy_enabled"] is True
    assert "personal and team" in response.text and "summary" in response.text
    assert "private-secret" not in response.text
    assert (await client.get(path)).status_code == 401
