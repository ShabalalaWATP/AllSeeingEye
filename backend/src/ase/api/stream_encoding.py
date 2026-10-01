"""Stream payloads: turn bus messages into JSON once and share the text across streams.

Every open stream reads the same published message object. The first stream to reach
a public message pays for its JSON; later streams with the same category filter reuse
the text. An upsert encodes each event once and joins the selection for each filter,
which yields exactly the text `json.dumps(serialise(...), ensure_ascii=False)` would.
Alerts are authorised per user and are never cached here.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any

from ase.api.schemas_events import EventOut, SourceHealthOut
from ase.api.schemas_warning import AlertOut
from ase.application.feeds.health import SourceHealth
from ase.application.ports.feeds import BusMessage
from ase.domain.events import Category, Event
from ase.domain.warning import Alert

PUBLIC_KINDS = frozenset({"event.upsert", "event.expire", "event.resync", "source.health"})
RESYNC_REASONS = ("expiry_overflow", "stream_gap", "snapshot_required")
MAX_CACHED_MESSAGES = 128
MAX_CACHED_CHARS = 8 * 1024 * 1024
_UNFILTERED: frozenset[Category] = frozenset()


def dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False)


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


def _serialise_soft_resync(
    message: BusMessage, wanted: frozenset[Category]
) -> dict[str, Any] | None:
    """Name the affected partitions this subscriber shows, or drop an unrelated hint.

    Without recognisable partitions every subscriber receives the bare hint and
    reconciles fully. An empty filter keeps its meaning of every category.
    """
    payload: dict[str, Any] = {"reason": "snapshot_required"}
    categories = message.payload.get("categories")
    if (
        not isinstance(categories, tuple | list | frozenset | set)
        or not categories
        or not all(isinstance(category, Category) for category in categories)
    ):
        return payload
    affected = frozenset(categories) & wanted if wanted else frozenset(categories)
    if not affected:
        return None
    payload["categories"] = sorted(category.value for category in affected)
    source_id = message.payload.get("source_id")
    if isinstance(source_id, str):
        payload["source_id"] = source_id
    return payload


def _serialise_resync(message: BusMessage, wanted: frozenset[Category]) -> dict[str, Any] | None:
    reason = message.payload.get("reason")
    if reason == "snapshot_required":
        return _serialise_soft_resync(message, wanted)
    # Real gaps and expiry overflows always clear and reload, whatever the filter.
    return {"reason": reason} if reason in RESYNC_REASONS else None


def _filtered(message: BusMessage) -> bool:
    """Upserts and partition-scoped refresh hints differ by category filter."""
    return message.kind == "event.upsert" or (
        message.kind == "event.resync" and message.payload.get("reason") == "snapshot_required"
    )


def serialise(message: BusMessage, wanted: frozenset[Category]) -> dict[str, Any] | None:
    """Turn a bus message into a JSON-safe payload, or None when the filter drops it."""
    if message.kind == "event.upsert":
        return _serialise_upsert(message, wanted)
    if message.kind == "event.expire":
        ids = message.payload.get("ids")
        id_list = [str(i) for i in ids] if isinstance(ids, tuple | list) else []
        return {"ids": id_list, "count": len(id_list)}
    if message.kind == "event.resync":
        return _serialise_resync(message, wanted)
    if message.kind == "alert":
        alert = message.payload.get("alert")
        if isinstance(alert, Alert):
            return AlertOut.from_alert(alert).model_dump(mode="json")
    if message.kind == "source.health":
        health = message.payload.get("health")
        if isinstance(health, SourceHealth):
            return SourceHealthOut.from_health(health).model_dump(mode="json")
    return None


class _Encoded:
    __slots__ = ("chars", "events", "message", "texts")

    def __init__(self, message: BusMessage) -> None:
        # Holding the message keeps its id() unique for as long as this entry lives.
        self.message = message
        self.events: list[tuple[Category, str]] | None = None
        self.texts: dict[frozenset[Category], str | None] = {}
        self.chars = 0


class StreamEncoder:
    """A bounded cache of encoded public payloads keyed by message identity and filter."""

    def __init__(
        self, max_messages: int = MAX_CACHED_MESSAGES, max_chars: int = MAX_CACHED_CHARS
    ) -> None:
        self._max_messages = max_messages
        self._max_chars = max_chars
        # Keyed by id(message), not sequence: synthetic resync messages all carry sequence
        # 0. Each entry holds its message, so an id cannot be reused while it is cached.
        self._entries: OrderedDict[int, _Encoded] = OrderedDict()
        self._chars = 0
        self.encoded = 0  # Encodings performed rather than reused, for tests and tuning.

    @property
    def cached_chars(self) -> int:
        return self._chars

    def __len__(self) -> int:
        return len(self._entries)

    def encode(self, message: BusMessage, wanted: frozenset[Category]) -> str | None:
        """The JSON text for a public message under a filter, or None when it is dropped."""
        if message.kind not in PUBLIC_KINDS:
            raise ValueError(f"{message.kind} is not a public stream message")
        entry = self._entries.get(id(message))
        if entry is None:
            entry = self._entries[id(message)] = _Encoded(message)
        else:
            self._entries.move_to_end(id(message))
        # Upserts and refresh hints are filtered; other public kinds have one text for everyone.
        key = wanted if _filtered(message) else _UNFILTERED
        if key not in entry.texts:
            entry.texts[key] = self._encode(entry, key)
            self.encoded += 1
            self._account(entry)
        return entry.texts[key]

    @staticmethod
    def _encode(entry: _Encoded, wanted: frozenset[Category]) -> str | None:
        message = entry.message
        events = message.payload.get("events")
        if message.kind != "event.upsert" or not isinstance(events, list):
            payload = serialise(message, wanted)
            return None if payload is None else dumps(payload)
        if entry.events is None:
            entry.events = [
                (event.category, dumps(EventOut.from_event(event).model_dump(mode="json")))
                for event in events
                if isinstance(event, Event)
            ]
        selected = [text for category, text in entry.events if not wanted or category in wanted]
        if not selected:
            return None
        source = dumps(message.payload.get("source_id"))
        return '{"source_id": ' + source + ', "events": [' + ", ".join(selected) + "]}"

    def _account(self, entry: _Encoded) -> None:
        chars = sum(len(text) for _, text in entry.events or ())
        chars += sum(len(text or "") for text in entry.texts.values())
        self._chars += chars - entry.chars
        entry.chars = chars
        # The current entry is newest, so it stays even when it alone exceeds the budget.
        while len(self._entries) > 1 and (
            len(self._entries) > self._max_messages or self._chars > self._max_chars
        ):
            _, evicted = self._entries.popitem(last=False)
            self._chars -= evicted.chars
