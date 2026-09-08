"""Bounded server-side collection of global AISStream position reports."""

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any

from websockets.asyncio.client import connect

from ase.adapters.feeds.aisstream_positions import parse_position
from ase.adapters.feeds.http import FeedFetchError, assert_public_host
from ase.application.ports import Clock
from ase.domain.events import Category, Event, Reliability
from ase.domain.sources import SourceKind, SourceSpec

URL = "wss://stream.aisstream.io/v0/stream"
SPEC = SourceSpec(
    id="aisstream",
    name="AISStream: global ship positions",
    organisation="AISStream",
    category=Category.MARITIME,
    kind=SourceKind.WEBSOCKET,
    url=URL,
    homepage="https://aisstream.io/",
    reliability=Reliability.F,
    poll_interval=timedelta(seconds=30),
    requires_key=True,
    instrument=True,
    licence_note="Provider terms apply. Receiver-dependent coverage; sampled collection.",
    flags=frozenset({"ais", "global_coverage", "reported_identity", "sampled"}),
)
COLLECTION_SECONDS = 40
MAX_MESSAGES = 50_000
MAX_VESSELS = 20_000
# Never let WebSocket debug frame logs disclose subscription credentials.
_LOGGER = logging.Logger("ase.aisstream.transport", level=logging.CRITICAL + 1)


class _DirectConnection(connect):
    def process_redirect(self, exc: Exception) -> Exception:
        return FeedFetchError("AISStream redirect refused")


class AisStreamConnector:
    spec = SPEC

    def __init__(self, key: str, clock: Clock) -> None:
        self._key, self._clock = key, clock

    async def fetch(self) -> list[Event]:
        events: dict[str, Event] = {}
        try:
            address = await assert_public_host("https://stream.aisstream.io/v0/stream")
            async with _DirectConnection(
                URL,
                host=address,
                server_hostname="stream.aisstream.io",
                proxy=None,
                compression="deflate",
                max_size=65_536,
                max_queue=16,
                open_timeout=8,
                close_timeout=2,
                logger=_LOGGER,
            ) as socket:
                await socket.send(
                    json.dumps(
                        {
                            "APIKey": self._key,
                            "BoundingBoxes": [[[-90, -180], [90, 180]]],
                            "FilterMessageTypes": [
                                "PositionReport",
                                "StandardClassBPositionReport",
                                "ExtendedClassBPositionReport",
                            ],
                        }
                    )
                )
                try:
                    async with asyncio.timeout(COLLECTION_SECONDS):
                        for _ in range(MAX_MESSAGES):
                            data: Any = json.loads(await socket.recv())
                            if not isinstance(data, dict) or "error" in data or "Error" in data:
                                raise FeedFetchError("AISStream refused the subscription")
                            event = parse_position(data, self._clock.now())
                            if event is not None:
                                previous = events.get(event.id)
                                if previous is None or (
                                    event.published_at is not None
                                    and previous.published_at is not None
                                    and event.published_at >= previous.published_at
                                ):
                                    events[event.id] = event
                            if len(events) >= MAX_VESSELS:
                                break
                except TimeoutError:
                    pass
        except Exception:
            # Provider errors can echo credentials; never put their bodies in health/logs.
            raise FeedFetchError(
                "AISStream connection unavailable; check key and provider status"
            ) from None
        if not events:
            raise FeedFetchError(
                "AISStream returned no fresh vessel positions in the collection window"
            )
        return list(events.values())
