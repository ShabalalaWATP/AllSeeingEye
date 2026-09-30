"""Standard Web Push encryption with public DNS pinning and no private payload fields."""

import asyncio
import base64
import binascii
from datetime import datetime
from typing import cast
from urllib.parse import urlsplit

import httpx
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid
from pywebpush import WebPusher

from ase.adapters.feeds.http import FeedFetchError, assert_public_host, pin_url
from ase.adapters.feeds.secret_urls import protect_http_logs
from ase.adapters.tls import verified_ssl_context
from ase.domain.errors import InvalidRequest
from ase.domain.web_push import PushDelivery, PushOutcome, PushSubscription


def checked_endpoint(endpoint: str) -> str:
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError:
        raise InvalidRequest("Invalid push endpoint.") from None
    if (
        len(endpoint) > 2048
        or parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.fragment
        or port not in (None, 443)
        or any(not 32 < ord(char) < 127 for char in endpoint)
    ):
        raise InvalidRequest("Push endpoints require public HTTPS on port 443.")
    host = parts.hostname
    if host not in {"fcm.googleapis.com", "updates.push.services.mozilla.com"} and not any(
        host.endswith(suffix) for suffix in (".push.apple.com", ".notify.windows.com")
    ):
        raise InvalidRequest("This browser push provider is not supported.")
    return parts.hostname


def checked_keys(subscription: PushSubscription) -> None:
    try:
        public = base64.b64decode(subscription.p256dh + "=", altchars=b"-_", validate=True)
        auth = base64.b64decode(subscription.auth + "==", altchars=b"-_", validate=True)
        if len(public) != 65 or len(auth) != 16:
            raise ValueError()
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public)
    except (ValueError, binascii.Error):
        raise InvalidRequest("Invalid browser push keys.") from None


class WebPushValidator:
    async def validate(self, subscription: PushSubscription) -> None:
        checked_endpoint(subscription.endpoint)
        checked_keys(subscription)
        try:
            async with asyncio.timeout(10):
                await assert_public_host(subscription.endpoint)
        except (FeedFetchError, TimeoutError):
            raise InvalidRequest("Push endpoints must resolve only to public addresses.") from None


class WebPushSender:
    def __init__(
        self, private_key: str, subject: str, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        # The library parses a configured key; it is never generated on app startup.
        self._vapid = Vapid.from_string(private_key)
        self._subject, self._transport = subject, transport

    @property
    def public_key(self) -> str:
        raw = self._vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    async def send(self, delivery: PushDelivery, now: datetime) -> PushOutcome:
        with protect_http_logs():
            return await self._send(delivery, now)

    async def _send(self, delivery: PushDelivery, now: datetime) -> PushOutcome:
        subscription = delivery.subscription
        try:
            host = checked_endpoint(subscription.endpoint)
            address = await assert_public_host(subscription.endpoint)
            checked_keys(subscription)
            body = cast(
                bytes,
                WebPusher(
                    {
                        "endpoint": subscription.endpoint,
                        "keys": {
                            "p256dh": subscription.p256dh,
                            "auth": subscription.auth,
                        },
                    }
                ).encode(str(delivery.alert_id).encode("ascii"))["body"],
            )
            headers = dict(
                self._vapid.sign(
                    {
                        "aud": f"https://{host}",
                        "sub": self._subject,
                        "exp": int(now.timestamp()) + 3600,
                    }
                )
            )
            headers.update(
                {
                    "Host": host,
                    "Content-Encoding": "aes128gcm",
                    "TTL": "0",
                    "Content-Type": "application/octet-stream",
                    "Accept-Encoding": "identity",
                }
            )
            target = (
                subscription.endpoint
                if address is None
                else pin_url(subscription.endpoint, address)
            )
            async with (
                httpx.AsyncClient(
                    timeout=10,
                    transport=self._transport,
                    trust_env=False,
                    verify=verified_ssl_context(trust_env=False),
                ) as client,
                client.stream(
                    "POST",
                    target,
                    content=body,
                    headers=headers,
                    extensions={"sni_hostname": host},
                    follow_redirects=False,
                ) as response,
            ):
                status = response.status_code
        except (FeedFetchError, InvalidRequest):
            return PushOutcome.REFUSED
        except (httpx.HTTPError, TimeoutError):
            return PushOutcome.UNCERTAIN
        if status in (404, 410):
            return PushOutcome.EXPIRED
        return PushOutcome.SENT if 200 <= status < 300 else PushOutcome.REFUSED
