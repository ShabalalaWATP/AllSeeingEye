"""Shared plumbing for HTTP feed connectors.

Most connectors take the shared feed client and a clock and nothing else, report an
unchanged upstream (HTTP 304) as an empty batch and read one list from a JSON object.
These helpers hold that boilerplate only; each connector keeps its own parsing, ids and
error handling.
"""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import Event


class HttpFeed:
    """Holds the shared feed client and clock for connectors that need nothing else."""

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock


def empty_when_unchanged[C](
    fetch: Callable[[C], Awaitable[list[Event]]],
) -> Callable[[C], Coroutine[Any, Any, list[Event]]]:
    """Report an unchanged upstream (HTTP 304) as an empty batch rather than a failure.

    It covers the whole method, so use it only where every request the method makes is
    the conditional fetch itself or handles `NotModified` on its own.
    """

    @functools.wraps(fetch)
    async def fetch_or_empty(connector: C) -> list[Event]:
        try:
            return await fetch(connector)
        except NotModified:
            return []

    return fetch_or_empty


def json_list(payload: object, key: str) -> Any:
    """`payload[key]` (empty when absent) from a JSON object; any other payload is empty.

    The member is returned exactly as the upstream sent it, so a GeoJSON collection's
    `features` or an API envelope's `results` keep each connector's own item checks.
    """
    return payload.get(key, []) if isinstance(payload, dict) else []
