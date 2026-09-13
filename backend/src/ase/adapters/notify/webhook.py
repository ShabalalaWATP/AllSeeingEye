"""Alert routing to a webhook: one JSON POST per alert to a public address, never retried."""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

import httpx
import structlog

from ase.adapters.feeds.http import FeedFetchError, assert_public_host, pin_url
from ase.domain.warning import Alert, Indicator

log = structlog.get_logger(__name__)

TIMEOUT_SECONDS = 10.0


def alert_payload(alert: Alert, indicator: Indicator) -> dict[str, object]:
    """What a receiver gets: the alert and the indicator's name, never any credential."""
    return {
        "kind": "alert",
        "id": str(alert.id),
        "indicator": {"id": str(indicator.id), "name": indicator.name},
        "title": alert.title,
        "summary": alert.summary,
        "count": alert.count,
        "threshold": alert.threshold,
        "fired_at": alert.fired_at.isoformat(),
        "countries": list(alert.countries),
        "event_ids": list(alert.event_ids),
    }


class WebhookNotifier:
    def __init__(
        self, url: str, user_agent: str, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError("Alert webhooks must use HTTPS.")
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError("Alert webhooks need a valid HTTPS port.") from exc
        host = parts.hostname
        try:
            host_ascii = host if ":" in host else host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("Alert webhook hostname is invalid.") from exc
        authority = f"[{host_ascii}]" if ":" in host_ascii else host_ascii
        if port is not None:
            authority = f"{authority}:{port}"
        self._url = url
        self._hostname = host_ascii
        self._authority = authority
        self._user_agent = user_agent
        self._transport = transport

    async def notify(self, alert: Alert, indicator: Indicator) -> bool:
        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                address = await assert_public_host(self._url)
                target = self._url if address is None else pin_url(self._url, address)
                headers = {
                    "User-Agent": self._user_agent,
                    "Host": self._authority,
                    "Accept-Encoding": "identity",
                }
                async with (
                    httpx.AsyncClient(
                        timeout=TIMEOUT_SECONDS, transport=self._transport, headers=headers
                    ) as client,
                    client.stream(
                        "POST",
                        target,
                        json=alert_payload(alert, indicator),
                        extensions={"sni_hostname": self._hostname},
                        follow_redirects=False,
                    ) as response,
                ):
                    status = response.status_code
        except FeedFetchError as exc:
            log.warning("alert_webhook_refused", reason=str(exc))
            return False
        except (httpx.HTTPError, TimeoutError) as exc:
            log.warning("alert_webhook_failed", error=type(exc).__name__)
            return False
        if not 200 <= status < 300:
            log.warning("alert_webhook_rejected", status=status)
            return False
        return True


class NullNotifier:
    """No route configured: the alert still lands in the app and on the stream."""

    async def notify(self, alert: Alert, indicator: Indicator) -> bool:
        return False
