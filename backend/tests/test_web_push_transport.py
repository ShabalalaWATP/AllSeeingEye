"""Encrypted opaque payloads use pinned public TLS and suppress credential-shaped HTTP logs."""

import base64
import logging
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.notify.web_push import WebPushSender
from ase.domain.web_push import PushDelivery, PushOutcome, PushSubscription
from test_web_push import subscription


def sender(transport):
    key = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        Encoding.DER,
        PrivateFormat.PKCS8,
        NoEncryption(),
    )
    return WebPushSender(
        base64.urlsafe_b64encode(key).decode(),
        "mailto:operator@example.invalid",
        transport=transport,
    )


def delivery():
    details = subscription()
    return PushDelivery(uuid4(), uuid4(), uuid4(), uuid4(), PushSubscription(**details))


@pytest.mark.parametrize(
    "status,expected",
    [
        (201, PushOutcome.SENT),
        (410, PushOutcome.EXPIRED),
        (302, PushOutcome.REFUSED),
        (429, PushOutcome.REFUSED),
    ],
)
async def test_transport_pins_every_send_and_never_follows_redirects(
    monkeypatch, caplog, status, expected
):
    calls = []
    resolutions = []

    async def resolve(url):
        resolutions.append(url)
        return "8.8.8.8"

    def receive(request):
        calls.append(request)
        return httpx.Response(status, headers={"Location": "http://127.0.0.1/private"})

    monkeypatch.setattr("ase.adapters.notify.web_push.assert_public_host", resolve)
    mail = delivery()
    with caplog.at_level(logging.DEBUG):
        assert await sender(httpx.MockTransport(receive)).send(mail, datetime.now(UTC)) is expected
    assert len(resolutions) == len(calls) == 1
    request = calls[0]
    assert request.url.host == "8.8.8.8"
    assert request.headers["host"] == "fcm.googleapis.com"
    assert request.extensions["sni_hostname"] == "fcm.googleapis.com"
    assert request.headers["content-encoding"] == "aes128gcm"
    assert request.headers["ttl"] == "0"
    assert str(mail.alert_id).encode() not in request.content
    assert "test-device" not in caplog.text and "vapid t=" not in caplog.text


async def test_rebinding_to_private_address_stops_transport(monkeypatch):
    called = []

    async def refuse(_url):
        raise FeedFetchError("non-public")

    monkeypatch.setattr("ase.adapters.notify.web_push.assert_public_host", refuse)
    transport = httpx.MockTransport(called.append)
    assert await sender(transport).send(delivery(), datetime.now(UTC)) is PushOutcome.REFUSED
    assert not called


async def test_plaintext_is_exactly_opaque_uuid(monkeypatch):
    plaintext = []

    async def resolve(_url):
        return "8.8.8.8"

    def encode(_self, body):
        plaintext.append(body)
        return {"body": b"encrypted-test-data"}

    monkeypatch.setattr("ase.adapters.notify.web_push.assert_public_host", resolve)
    monkeypatch.setattr("ase.adapters.notify.web_push.WebPusher.encode", encode)
    item = delivery()
    assert (
        await sender(httpx.MockTransport(lambda _: httpx.Response(201))).send(
            item, datetime.now(UTC)
        )
        is PushOutcome.SENT
    )
    assert plaintext == [str(item.alert_id).encode("ascii")]
