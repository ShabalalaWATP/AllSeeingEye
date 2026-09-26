"""Server-Sent Events: live upserts, expiries and source health for the browser.

Frames carry an `id` (see `api/stream_resume.py`). A browser that reconnects with it
as Last-Event-ID while the bus still holds every later public message receives those
messages after `hello` with `resumed: true`, instead of reloading its snapshot. Any
other id gets `resumed: false` followed by `event.resync` with `snapshot_required`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import aclosing
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Header, Query
from sse_starlette.sse import EventSourceResponse

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.routers.events import parse_categories
from ase.api.stream_encoding import PUBLIC_KINDS, StreamEncoder, dumps, serialise
from ase.api.stream_session import LiveStream
from ase.application.access import AccessContext
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.ports.feeds import BusMessage
from ase.container import Container
from ase.domain.errors import NotFound, RateLimited, Unauthenticated
from ase.domain.events import Category
from ase.domain.warning import Alert

router = APIRouter(tags=["stream"])
PING_SECONDS = 15
STREAM_RETRY_SECONDS = 15
# Shared by every stream in the process: public payloads are encoded once per filter.
ENCODER = StreamEncoder()


async def _stream_access(claims: AccessClaims, container: Container) -> AccessContext | None:
    # A stream cannot reuse the request transaction: each re-check must observe
    # committed logout, credential changes and account deactivation.
    async with container.session_factory() as session:
        repos = container.repositories(session)
        try:
            actor = await validate_current_session(
                claims, repos.users, repos.refresh_tokens, container.clock
            )
            return await container.access_policy(session).context(actor)
        except Unauthenticated:
            return None


async def _authorised_payload(
    message: BusMessage, wanted: frozenset[Category], claims: AccessClaims, container: Container
) -> dict[str, Any] | None:
    if message.kind == "alert":
        alert = message.payload.get("alert")
        if not isinstance(alert, Alert):
            return None
        # An access.changed frame can yield to a slow client before this payload.
        # Re-read here so a queued alert never borrows authority from before that yield.
        access = await _stream_access(claims, container)
        if access is None:
            return None
        try:
            access.require_read(alert.created_by, alert.team_id)
        except NotFound:
            return None
    return serialise(message, wanted)


async def _frame_data(
    message: BusMessage, wanted: frozenset[Category], claims: AccessClaims, container: Container
) -> str | None:
    if message.kind in PUBLIC_KINDS:
        return ENCODER.encode(message, wanted)
    # Alerts are private: authorise and encode them for this stream alone.
    payload = await _authorised_payload(message, wanted, claims, container)
    return None if payload is None else dumps(payload)


@router.get("/stream")
async def stream(
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    categories: Annotated[str | None, Query(max_length=200)] = None,
    last_event_id: Annotated[
        str | None,
        Header(description="The last frame id received, to resume within the replay window."),
    ] = None,
) -> EventSourceResponse:
    wanted = parse_categories(categories)
    now = container.clock.now()
    # The stream ends when the presented token does, never later than a full lifetime.
    lifetime = timedelta(minutes=container.settings.access_token_minutes)
    deadline = min(claims.expires_at, now + lifetime)
    if not container.streams.acquire(user.id):
        raise RateLimited(retry_after=STREAM_RETRY_SECONDS)

    async def read_access() -> AccessContext | None:
        return await _stream_access(claims, container)

    async def encode(message: BusMessage) -> str | None:
        return await _frame_data(message, wanted, claims, container)

    live = LiveStream(
        container,
        claims,
        deadline=deadline,
        expires_in=int((deadline - now).total_seconds()),
        ping_seconds=PING_SECONDS,
        read_access=read_access,
        encode=encode,
    )

    async def generate() -> AsyncIterator[dict[str, str]]:
        try:
            async with aclosing(live.frames(last_event_id)) as frames:
                async for frame in frames:
                    yield frame
        finally:
            container.streams.release(user.id)

    return EventSourceResponse(generate(), ping=PING_SECONDS)
