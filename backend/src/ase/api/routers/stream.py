"""Server-Sent Events: live upserts, expiries and source health for the browser."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.routers.events import parse_categories
from ase.api.schemas_events import EventOut, SourceHealthOut
from ase.api.schemas_warning import AlertOut
from ase.application.feeds.health import SourceHealth
from ase.application.ports.feeds import BusMessage
from ase.domain.errors import RateLimited
from ase.domain.events import Category, Event
from ase.domain.warning import Alert

router = APIRouter(tags=["stream"])
PING_SECONDS = 15
STREAM_RETRY_SECONDS = 15


def _serialise_upsert(message: BusMessage, wanted: frozenset[Category]) -> dict[str, Any] | None:
    events = message.payload.get("events")
    if not isinstance(events, list):
        return None
    selected = [
        EventOut.from_event(e).model_dump(mode="json")
        for e in events
        if isinstance(e, Event) and (not wanted or e.category in wanted)
    ]
    if not selected:
        return None
    return {"source_id": message.payload.get("source_id"), "events": selected}


def serialise(message: BusMessage, wanted: frozenset[Category]) -> dict[str, Any] | None:
    """Turn a bus message into a JSON-safe payload, or None when the filter drops it."""
    if message.kind == "event.upsert":
        return _serialise_upsert(message, wanted)
    if message.kind == "event.expire":
        ids = message.payload.get("ids")
        id_list = [str(i) for i in ids] if isinstance(ids, tuple | list) else []
        return {"ids": id_list, "count": len(id_list)}
    if message.kind == "alert":
        alert = message.payload.get("alert")
        if isinstance(alert, Alert):
            return AlertOut.from_alert(alert).model_dump(mode="json")
    if message.kind == "source.health":
        health = message.payload.get("health")
        if isinstance(health, SourceHealth):
            return SourceHealthOut.from_health(health).model_dump(mode="json")
    return None


@router.get("/stream")
async def stream(
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    categories: Annotated[str | None, Query(max_length=200)] = None,
) -> EventSourceResponse:
    wanted = parse_categories(categories)
    now = container.clock.now()
    # The stream ends when the presented token does, never later than a full lifetime.
    lifetime = timedelta(minutes=container.settings.access_token_minutes)
    deadline = min(claims.expires_at, now + lifetime)
    if not container.streams.acquire(user.id):
        raise RateLimited(retry_after=STREAM_RETRY_SECONDS)

    async def generate() -> AsyncIterator[dict[str, str]]:
        subscription = container.bus.subscribe()
        try:
            yield {
                "event": "hello",
                "data": json.dumps({"expires_in": int((deadline - now).total_seconds())}),
            }
            while True:
                remaining = (deadline - container.clock.now()).total_seconds()
                if remaining <= 0:
                    yield {"event": "bye", "data": json.dumps({"reason": "token_expired"})}
                    return
                # Wake at least every ping so the deadline is honoured on a quiet stream.
                try:
                    async with asyncio.timeout(min(remaining, PING_SECONDS)):
                        message = await anext(aiter(subscription))
                except TimeoutError:
                    continue
                except StopAsyncIteration:
                    return
                payload = serialise(message, wanted)
                if payload is not None:
                    yield {"event": message.kind, "data": json.dumps(payload)}
        finally:
            subscription.close()
            container.streams.release(user.id)

    return EventSourceResponse(generate(), ping=PING_SECONDS)
