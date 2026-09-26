"""Public stream payloads are encoded once per filter; alerts stay per client."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.api import stream_encoding
from ase.api.routers import stream as stream_router
from ase.api.stream_encoding import StreamEncoder, serialise
from ase.application.feeds.health import SourceHealth
from ase.application.ports.feeds import BusMessage
from ase.container import Container
from ase.domain.events import Category
from ase.domain.users import User
from ase.domain.warning import Alert
from feeds_helpers import make_event
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, login_token

FILTERS = (
    frozenset(),
    frozenset({Category.DISASTER}),
    frozenset({Category.CYBER, Category.MARITIME}),
    frozenset({Category.SPACE}),
)


def _upsert(source_id: str | None = "fake_feed") -> BusMessage:
    events = [
        make_event("quake", title="Séisme près de Nîmes"),
        make_event("intrusion", category=Category.CYBER, title="東京 outage"),
        make_event("vessel", category=Category.MARITIME, summary='Quoted "cargo"\n'),
        "not an event",
    ]
    return BusMessage("event.upsert", {"source_id": source_id, "events": events})


def _per_client(message: BusMessage, wanted: frozenset[Category]) -> str | None:
    payload = serialise(message, wanted)
    return None if payload is None else json.dumps(payload, ensure_ascii=False)


@pytest.mark.parametrize(
    "message",
    [
        _upsert(),
        _upsert(None),
        BusMessage("event.upsert", {"events": "not a list"}),
        BusMessage("event.upsert", {"events": []}),
        BusMessage("event.expire", {"ids": ("a", "b"), "count": 2}),
        BusMessage("event.expire", {"ids": None}),
        BusMessage("event.resync", {"reason": "expiry_overflow"}),
        BusMessage("event.resync", {"reason": "secret text"}),
        BusMessage("source.health", {"health": SourceHealth("fake_feed", polls=3)}),
        BusMessage("source.health", {"health": "not health"}),
    ],
)
def test_shared_text_is_byte_identical_to_per_client_json(message: BusMessage) -> None:
    encoder = StreamEncoder()
    for wanted in FILTERS:
        assert encoder.encode(message, wanted) == _per_client(message, wanted)


def test_each_event_and_filter_is_encoded_once(monkeypatch: pytest.MonkeyPatch) -> None:
    conversions = 0
    original = stream_encoding.EventOut.from_event

    def counted(event):  # type: ignore[no-untyped-def]
        nonlocal conversions
        conversions += 1
        return original(event)

    encoder, message = StreamEncoder(), _upsert()
    unfiltered = _per_client(message, frozenset())
    monkeypatch.setattr(stream_encoding.EventOut, "from_event", counted)
    disaster = frozenset({Category.DISASTER})
    first = encoder.encode(message, disaster)
    assert encoder.encode(message, disaster) is first
    assert (encoder.encoded, conversions) == (1, 3)
    # Another filter joins the already encoded events instead of converting them again.
    assert encoder.encode(message, frozenset()) == unfiltered
    assert (encoder.encoded, conversions) == (2, 3)
    # Unfiltered kinds share a single text whatever the stream's filter.
    expire = BusMessage("event.expire", {"ids": ["x"]})
    texts = {id(encoder.encode(expire, wanted)) for wanted in FILTERS}
    assert len(texts) == 1 and encoder.encoded == 3


def test_cache_is_bounded_by_messages_and_characters() -> None:
    encoder = StreamEncoder(max_messages=2)
    messages = [BusMessage("event.expire", {"ids": [str(i)]}) for i in range(3)]
    for message in messages:
        encoder.encode(message, frozenset())
    assert len(encoder) == 2 and encoder.encoded == 3
    encoder.encode(messages[0], frozenset())  # Evicted, so encoded again.
    assert encoder.encoded == 4

    small = StreamEncoder(max_chars=10)
    big = BusMessage("event.expire", {"ids": ["x" * 50]})
    text = small.encode(big, frozenset())
    assert text is not None and len(small) == 1 and small.cached_chars == len(text)
    second = BusMessage("event.expire", {"ids": ["y"]})
    small.encode(second, frozenset())
    assert len(small) == 1 and small.cached_chars == len(_per_client(second, frozenset()) or "")


def test_private_messages_are_refused() -> None:
    alert = Alert(uuid4(), uuid4(), make_event().observed_at, "Private", "", 1, 1, (), ())
    with pytest.raises(ValueError, match="alert"):
        StreamEncoder().encode(BusMessage("alert", {"alert": alert}), frozenset())


async def test_streams_share_public_text_and_authorise_alerts_per_client(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    user_token = await login_token(client, user.email, USER_PASSWORD)
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    streams = [
        await stream_router.stream(user, container.issuer.verify(user_token), container),
        await stream_router.stream(admin, container.issuer.verify(admin_token), container),
    ]
    iterators = [response.body_iterator for response in streams]
    before = stream_router.ENCODER.encoded
    try:
        for iterator in iterators:
            assert (await anext(iterator))["event"] == "hello"
        await container.bus.publish(_upsert())
        async with asyncio.timeout(2):
            frames = [await anext(iterator) for iterator in iterators]
        assert frames[0]["data"] is frames[1]["data"]
        assert frames[0]["data"] == _per_client(_upsert(), frozenset())
        assert stream_router.ENCODER.encoded == before + 1
        alert = Alert(uuid4(), uuid4(), container.clock.now(), "Admin only", "", 1, 1, (), ())
        private = BusMessage("alert", {"alert": replace(alert, created_by=admin.id)})
        await container.bus.publish(private)
        await container.bus.publish(BusMessage("event.expire", {"ids": []}))
        async with asyncio.timeout(2):
            assert (await anext(iterators[0]))["event"] == "event.expire"
            delivered = await anext(iterators[1])
        assert delivered["event"] == "alert"
        assert json.loads(delivered["data"])["title"] == "Admin only"
    finally:
        for iterator in iterators:
            await iterator.aclose()
    assert container.streams.held(user.id) == container.streams.held(admin.id) == 0
