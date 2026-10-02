"""Push is per session, opaque, opt-in and fenced before external delivery."""

import base64
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select

from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.web_push_delivery import SqlPushDeliveryStore
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.application.account.web_push import WebPushWorker
from ase.domain.web_push import PushOutcome
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_private_feed import _alert

PATH = "/api/me/notifications/push"


def subscription(endpoint="https://fcm.googleapis.com/fcm/send/test-device"):
    public = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(
            Encoding.X962,
            PublicFormat.UncompressedPoint,
        )
    )

    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    return {"endpoint": endpoint, "p256dh": encode(public), "auth": encode(b"test bytes only!")}


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(
        "ase.container.web_push.push_sender", lambda _: SimpleNamespace(public_key="test-public")
    )

    async def public(_url):
        return "8.8.8.8"

    monkeypatch.setattr("ase.adapters.notify.web_push.assert_public_host", public)


class Sender:
    def __init__(self, outcome=PushOutcome.SENT):
        self.messages = []
        self.outcome = outcome

    async def send(self, delivery, now):
        self.messages.append(delivery)
        return self.outcome


async def register(client, container):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(PATH, headers=bearer(token), json=subscription())
    assert response.status_code == 200, response.text
    return container.issuer.verify(token), response.json()


def worker(container, sender):
    store = SqlPushDeliveryStore(
        container.session_factory, container.access_policy, container.cipher
    )
    return WebPushWorker(store, sender, container.clock), store


async def test_default_unavailable_and_no_devices(client, container, user):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    result = await client.get(PATH, headers=bearer(token))
    assert result.json() == {"available": False, "public_key": None, "devices": []}
    assert result.headers["cache-control"] == "private, no-store"
    assert (await client.post(PATH, headers=bearer(token), json=subscription())).status_code == 422


async def test_registration_encrypts_endpoint_and_only_new_alert_ids_send(
    client, container, user, configured
):
    await _alert(container, user)
    container.clock.advance(timedelta(seconds=1))
    _claims, device = await register(client, container)
    async with container.session_factory() as session:
        stored = await session.get(PushDeviceRow, UUID(device["id"]))
        assert "fcm.googleapis.com" not in stored.encrypted_subscription
        assert "p256dh" not in stored.encrypted_subscription
    await _alert(container, user)
    sender = Sender()
    runner, _store = worker(container, sender)
    assert await runner.tick() == 1
    assert len(sender.messages) == 1
    assert isinstance(sender.messages[0].alert_id, UUID)
    assert await runner.tick() == 0
    assert "endpoint" not in device and "auth" not in device


@pytest.mark.parametrize(
    "transition", ["revoke_family", "revoke_all", "security_version", "deactivate"]
)
async def test_security_transitions_delete_device_and_fence_claim(
    client, container, user, configured, transition
):
    claims, _device = await register(client, container)
    await _alert(container, user)
    runner, store = worker(container, Sender())
    await store.enqueue(container.clock.now())
    delivery = await store.claim(container.clock.now())
    assert delivery is not None
    async with container.session_factory() as session:
        repos = container.repositories(session)
        if transition == "revoke_family":
            await repos.refresh_tokens.revoke_family(claims.family_id, container.clock.now())
        elif transition == "revoke_all":
            await repos.refresh_tokens.revoke_all_for_user(user.id, container.clock.now())
        else:
            fresh = await repos.users.get_by_id(user.id)
            changed = (
                replace(fresh, security_version=fresh.security_version + 1)
                if transition == "security_version"
                else replace(fresh, is_active=False)
            )
            await repos.users.save(changed)
        await session.commit()
        assert not list(await session.scalars(select(PushDeviceRow)))
        assert not list(await session.scalars(select(PushDeliveryRow)))
    assert not await store.authorise(delivery, container.clock.now())
    assert await runner.tick() == 0


async def test_removed_device_and_gone_provider_do_not_retry(client, container, user, configured):
    _claims, device = await register(client, container)
    await _alert(container, user)
    sender = Sender(PushOutcome.EXPIRED)
    runner, _store = worker(container, sender)
    await runner.tick()
    assert len(sender.messages) == 1
    async with container.session_factory() as session:
        assert await session.get(PushDeviceRow, UUID(device["id"])) is None
    assert await runner.tick() == 0


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/path",
        "https://127.0.0.1/path",
        "https://evil.example/path",
        "https://fcm.googleapis.com:8443/path",
        "https://fcm.googleapis.com.evil.example/path",
        "https://user@fcm.googleapis.com/path",
        "https://[bad",
    ],
)
async def test_non_provider_or_unsafe_endpoints_rejected(
    client, container, user, configured, endpoint
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    result = await client.post(PATH, headers=bearer(token), json=subscription(endpoint))
    assert result.status_code == 422


async def test_notification_detail_requires_current_object_access(client, container, user, admin):
    await _alert(container, admin)
    async with container.session_factory() as session:
        alert = await session.scalar(select(AlertRow))
        alert_id = alert.id
    assert (await client.get(f"/api/warning/alerts/{alert_id}")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (
        await client.get(f"/api/warning/alerts/{alert_id}", headers=bearer(token))
    ).status_code == 404
