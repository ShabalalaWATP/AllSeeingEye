"""The bus sequences every message and keeps a short, bounded public replay window."""

from __future__ import annotations

from uuid import uuid4

from ase.adapters.bus.memory import MAX_UPSERT_EVENTS, InMemoryEventBus
from ase.adapters.bus.replay import (
    EXPIRED_ID_BYTES,
    MESSAGE_OVERHEAD_BYTES,
    ReplayBuffer,
    estimate_message_bytes,
)
from ase.adapters.store.memory import estimate_bytes
from ase.application.ports.feeds import BusMessage
from ase.application.ports.session import SESSION_CHANGED
from ase.domain.events import Category
from ase.domain.warning import Alert
from feeds_helpers import NOW, make_event


class Monotonic:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _sequenced(kind: str, sequence: int, **payload: object) -> BusMessage:
    return BusMessage(kind, payload, sequence=sequence)


def test_only_public_messages_are_retained() -> None:
    buffer = ReplayBuffer()
    alert = Alert(uuid4(), uuid4(), NOW, "Private", "", 1, 1, (), ())
    buffer.record(_sequenced("alert", 1, alert=alert))
    buffer.record(_sequenced(SESSION_CHANGED, 2, user_id=uuid4()))
    buffer.record(_sequenced("something.else", 3))
    assert buffer.size == 0
    for sequence, kind in enumerate(
        ("event.upsert", "event.expire", "event.resync", "source.health"), start=4
    ):
        buffer.record(_sequenced(kind, sequence))
    assert [message.sequence for message in buffer.after(0) or []] == [4, 5, 6, 7]
    # Positions inside unretained private traffic are still complete.
    assert [message.sequence for message in buffer.after(2) or []] == [4, 5, 6, 7]


def test_count_bound_moves_the_floor() -> None:
    buffer = ReplayBuffer(max_messages=3)
    for sequence in range(1, 6):
        buffer.record(_sequenced("event.expire", sequence, ids=()))
    assert buffer.size == 3
    assert buffer.after(1) is None  # Message 2 is gone, so a resume from 1 would skip it.
    assert [message.sequence for message in buffer.after(2) or []] == [3, 4, 5]
    assert buffer.after(5) == []


def test_age_bound_expires_old_messages_on_read() -> None:
    clock = Monotonic()
    buffer = ReplayBuffer(max_age_seconds=120, monotonic=clock)
    buffer.record(_sequenced("event.expire", 1, ids=()))
    clock.now = 60
    buffer.record(_sequenced("event.expire", 2, ids=()))
    clock.now = 120
    assert [message.sequence for message in buffer.after(0) or []] == [1, 2]
    clock.now = 120.5
    assert buffer.after(0) is None
    assert [message.sequence for message in buffer.after(1) or []] == [2]
    clock.now = 181
    assert buffer.after(1) is None and buffer.after(2) == [] and buffer.size == 0


def test_byte_bound_and_oversized_messages() -> None:
    event = make_event("a")
    one = MESSAGE_OVERHEAD_BYTES + estimate_bytes(event)
    buffer = ReplayBuffer(max_bytes=2 * one)
    for sequence in (1, 2, 3):
        buffer.record(_sequenced("event.upsert", sequence, events=[event]))
    assert buffer.size == 2 and buffer.estimated_bytes == 2 * one
    assert buffer.after(1) is not None and buffer.after(0) is None
    # A single message larger than the budget is never retained and cannot be skipped.
    buffer.record(_sequenced("event.upsert", 4, events=[event, event, event]))
    assert buffer.size == 0 and buffer.estimated_bytes == 0
    assert buffer.after(3) is None and buffer.after(4) == []


def test_message_size_estimates_events_and_expired_ids() -> None:
    event = make_event("a")
    upsert = BusMessage("event.upsert", {"events": [event, "not an event"]})
    assert estimate_message_bytes(upsert) == MESSAGE_OVERHEAD_BYTES + estimate_bytes(event)
    expire = BusMessage("event.expire", {"ids": ("a", "b", "c")})
    assert estimate_message_bytes(expire) == MESSAGE_OVERHEAD_BYTES + 3 * EXPIRED_ID_BYTES
    assert estimate_message_bytes(BusMessage("source.health")) == MESSAGE_OVERHEAD_BYTES


async def test_bus_sequences_all_messages_and_replays_within_its_epoch() -> None:
    bus = InMemoryEventBus(epoch="abc123")
    assert (bus.epoch, bus.last_sequence) == ("abc123", 0)
    subscription = bus.subscribe()
    original = BusMessage("event.expire", {"ids": ["a"]})
    await bus.publish(original)
    bus.publish_nowait(BusMessage(SESSION_CHANGED, {"user_id": uuid4()}))
    await bus.publish(BusMessage("event.upsert", {"events": [make_event("b")]}))
    received = [await anext(subscription) for _ in range(3)]
    assert [message.sequence for message in received] == [1, 2, 3]
    assert original.sequence == 0  # Publishers' own objects are never modified.
    replayed = bus.replay("abc123", 1) or []
    assert [(message.kind, message.sequence) for message in replayed] == [("event.upsert", 3)]
    assert bus.replay("abc123", 0) is not None and bus.replay("abc123", 3) == []
    assert bus.replay("other", 1) is None  # A restarted process has a new epoch.
    assert bus.replay("abc123", 4) is None  # Not issued by this bus.
    assert bus.replay("abc123", -1) is None
    assert len(InMemoryEventBus().epoch) == 12
    assert InMemoryEventBus().epoch != InMemoryEventBus().epoch
    subscription.close()


async def test_oversized_batches_are_replayed_as_a_snapshot_request() -> None:
    bus = InMemoryEventBus()
    events = [make_event(str(i)) for i in range(MAX_UPSERT_EVENTS + 1)]
    await bus.publish(BusMessage("event.upsert", {"events": events}))
    replayed = bus.replay(bus.epoch, 0) or []
    assert [(message.kind, dict(message.payload)) for message in replayed] == [
        ("event.resync", {"reason": "snapshot_required", "categories": (Category.DISASTER,)})
    ]


async def test_gap_barrier_carries_the_latest_position() -> None:
    bus = InMemoryEventBus(max_queue=2)
    subscription = bus.subscribe()
    for key in "abcd":
        await bus.publish(BusMessage("event.upsert", {"events": [make_event(key)]}))
    barrier = await anext(subscription)
    assert barrier.payload == {"reason": "stream_gap"}
    assert barrier.sequence == bus.last_sequence == 4
    subscription.close()
