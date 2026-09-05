"""Alert routing to a webhook: one JSON POST per alert to a public address, never retried."""

from __future__ import annotations

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
        self._url = url
        self._user_agent = user_agent
        self._transport = transport

    async def notify(self, alert: Alert, indicator: Indicator) -> bool:
        try:
            address = await assert_public_host(self._url)
        except FeedFetchError as exc:
            log.warning("alert_webhook_refused", reason=str(exc))
            return False
        target = self._url if address is None else pin_url(self._url, address)
        host = urlsplit(self._url).hostname or ""
        headers = {"User-Agent": self._user_agent, "Host": host}
        try:
            async with httpx.AsyncClient(
                timeout=TIMEOUT_SECONDS, transport=self._transport, headers=headers
            ) as client:
                response = await client.post(target, json=alert_payload(alert, indicator))
        except httpx.HTTPError as exc:
            log.warning("alert_webhook_failed", error=type(exc).__name__)
            return False
        if not response.is_success:
            log.warning("alert_webhook_rejected", status=response.status_code)
            return False
        return True


class NullNotifier:
    """No route configured: the alert still lands in the app and on the stream."""

    async def notify(self, alert: Alert, indicator: Indicator) -> bool:
        return False
