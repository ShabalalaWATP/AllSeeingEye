"""Private SQLite fixtures for rule routing, without live SMTP or webhook requests."""

from uuid import UUID, uuid4

from sqlalchemy import select

from ase.adapters.persistence.alert_notification_delivery import SqlAlertDeliveryStore
from ase.adapters.persistence.alert_routing_models import AlertNotificationRow
from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.adapters.persistence.warning import SqlWarningStore
from ase.domain.notification_delivery import EmailPreferences
from ase.domain.warning import Alert
from helpers import USER_PASSWORD, bearer, login_token


async def rule(client, user, *, team_id=None):
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    created = await client.post(
        "/api/warning/indicators",
        headers=headers,
        json={"name": "Routing rule", "team_id": str(team_id) if team_id else None},
    )
    assert created.status_code == 201, created.text
    return headers, created.json()["id"]


async def enable_mail(container, user):
    async with container.session_factory() as session:
        await SqlMfaRepository(session).set_email_enabled(user.id, True)
        await SqlNotificationPreferences(session).save_email(user.id, EmailPreferences(True, False))
        await session.commit()


async def destination(client, headers, monkeypatch, *, team_id=None):
    async def public(_url):
        return "8.8.8.8"

    monkeypatch.setattr("ase.adapters.notify.alert_routing.assert_public_host", public)
    response = await client.post(
        "/api/warning/webhook-destinations",
        headers=headers,
        json={
            "name": "Operations",
            "url": "https://alerts.example.com/secret-hook",
            "team_id": str(team_id) if team_id else None,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def save_route(client, headers, rule_id, *, email=True, webhook=None, revision=0):
    response = await client.put(
        f"/api/warning/indicators/{rule_id}/notifications",
        headers=headers,
        json={"email_enabled": email, "webhook_id": webhook, "expected_revision": revision},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def fire(container, rule_id, *, installation=False):
    async with container.session_factory() as session:
        indicator = await container.repositories(session).indicators.get(UUID(rule_id))
    assert indicator is not None
    alert = Alert(
        uuid4(),
        indicator.id,
        container.clock.now(),
        "Private topic",
        "Private summary",
        1,
        1,
        ("event-1",),
        ("GB",),
        created_by=indicator.created_by,
        team_id=indicator.team_id,
    )
    store = SqlWarningStore(
        container.session_factory, container.access_policy, installation_copy=installation
    )
    assert await store.add_alert(alert, indicator)
    return alert


def delivery_store(container, *, installation_url=None):
    return SqlAlertDeliveryStore(
        container.session_factory,
        container.access_policy,
        container.cipher,
        installation_url=installation_url,
        base_url="http://app.test",
    )


async def outbox(container):
    async with container.session_factory() as session:
        return list(
            await session.scalars(
                select(AlertNotificationRow).order_by(AlertNotificationRow.channel)
            )
        )
