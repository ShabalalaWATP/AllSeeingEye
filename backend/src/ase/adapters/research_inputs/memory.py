"""A process-local private store with fixed slots, expiry and conservative memory accounting."""

from dataclasses import fields, replace
from datetime import timedelta
from types import MappingProxyType
from uuid import UUID, uuid4

from ase.adapters.research_inputs.previews import preview_size
from ase.application.ports import Clock
from ase.application.ports.research_inputs import (
    INPUT_TTL_SECONDS,
    MAX_INPUT_CHARACTERS,
    MAX_INPUT_EVENTS,
    MAX_PREVIEW_CHARACTERS,
    InputExtraction,
    InputReservation,
    ResearchInputReceipt,
    StoredResearchInput,
)
from ase.domain.errors import InvalidRequest, NotFound, RateLimited
from ase.domain.events import Event
from ase.domain.source_provenance_records import provenance_size
from ase.domain.users import User

MAX_GLOBAL_SLOTS = 8
MAX_USER_SLOTS = 2
MAX_ESTIMATED_BYTES = 8 * 1024 * 1024
MAX_SLOT_ESTIMATED_BYTES = 2 * 1024 * 1024


def _freeze_and_measure(extraction: InputExtraction) -> tuple[tuple[Event, ...], int]:
    if not 1 <= len(extraction.events) <= MAX_INPUT_EVENTS:
        raise InvalidRequest("The extracted input exceeds the passage limit or contains no text.")
    if (
        len(extraction.filename) > 120
        or len(extraction.media_type) > 120
        or len(extraction.sha256) != 64
        or any(char not in "0123456789abcdef" for char in extraction.sha256)
        or len(extraction.limitations) > 20
        or any(len(value) > 1000 for value in extraction.limitations)
    ):
        raise InvalidRequest("Extracted input metadata exceeds its limits.")
    events: list[Event] = []
    estimate = 4096 + preview_size(extraction.frames)
    estimate += sum(4 * len(value) for value in extraction.limitations)
    text_characters = 0
    for event in extraction.events:
        if len(event.title) > 300 or len(event.summary or "") > 1800:
            raise InvalidRequest("An extracted passage exceeds its text limit.")
        if len(event.transformations) > 4 or len(event.source_dates) > 4:
            raise InvalidRequest("Extracted provenance exceeds the passage limit.")
        estimate += provenance_size(event.transformations, event.source_dates)
        text_characters += len(event.summary or "")
        if len(event.attributes) > 40 or len(event.tags) > 40:
            raise InvalidRequest("Extracted input metadata exceeds its limits.")
        copied_attributes = dict(event.attributes)
        for key, value in copied_attributes.items():
            if not isinstance(key, str) or not isinstance(value, str | int | float | bool | None):
                raise InvalidRequest("Extracted input metadata must contain scalar values.")
            estimate += 128 + 4 * (len(key) + (len(value) if isinstance(value, str) else 32))
        for field in fields(event):
            value = getattr(event, field.name)
            if isinstance(value, str):
                estimate += 64 + 4 * len(value)
        estimate += 1536 + sum(64 + 4 * len(tag) for tag in event.tags)
        events.append(
            replace(
                event, attributes=MappingProxyType(copied_attributes), tags=frozenset(event.tags)
            )
        )
    if text_characters > MAX_INPUT_CHARACTERS or estimate > MAX_SLOT_ESTIMATED_BYTES:
        raise InvalidRequest("Extracted input exceeds the retained memory limit.")
    return tuple(events), estimate


class BoundedResearchInputStore:
    """Synchronous methods are atomic on the app event loop; never use from parser threads.

    All slots, including in-flight bodies/extractions, expire. No administrator
    override, list method, eviction of another live input or team lookup exists.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._reservations: dict[UUID, InputReservation] = {}
        self._ready: dict[UUID, StoredResearchInput] = {}
        self._sizes: dict[UUID, int] = {}

    def _expire(self) -> None:
        now = self._clock.now()
        expired = [key for key, value in self._reservations.items() if value.expires_at <= now]
        for key in expired:
            self._reservations.pop(key, None)
            self._ready.pop(key, None)
            self._sizes.pop(key, None)

    def reserve(self, actor: User, filename: str) -> InputReservation:
        self._expire()
        if not actor.is_active:
            raise NotFound()
        owned = sum(item.owner_id == actor.id for item in self._reservations.values())
        if len(self._reservations) >= MAX_GLOBAL_SLOTS or owned >= MAX_USER_SLOTS:
            raise RateLimited(INPUT_TTL_SECONDS)
        reservation = InputReservation(
            uuid4(),
            actor.id,
            actor.security_version,
            filename,
            self._clock.now() + timedelta(seconds=INPUT_TTL_SECONDS),
        )
        self._reservations[reservation.id] = reservation
        return reservation

    def require_pending(self, reservation: InputReservation) -> None:
        self._expire()
        if self._reservations.get(reservation.id) != reservation or reservation.id in self._ready:
            raise NotFound()

    def put(
        self, reservation: InputReservation, extraction: InputExtraction
    ) -> StoredResearchInput:
        self.require_pending(reservation)
        if extraction.filename != reservation.filename:
            raise InvalidRequest("The extracted input does not match the reserved filename.")
        events, estimate = _freeze_and_measure(extraction)
        if sum(self._sizes.values()) + estimate > MAX_ESTIMATED_BYTES:
            raise RateLimited(INPUT_TTL_SECONDS)
        receipt = ResearchInputReceipt(
            id=reservation.id,
            filename=extraction.filename,
            media_type=extraction.media_type,
            sha256=extraction.sha256,
            imported_at=self._clock.now(),
            expires_at=reservation.expires_at,
            event_count=len(events),
            extracted_characters=sum(len(event.summary or "") for event in events),
            preview="\n".join(event.summary or "" for event in events)[:MAX_PREVIEW_CHARACTERS],
            limitations=tuple(extraction.limitations),
            parent_input_id=extraction.parent_input_id,
        )
        result = StoredResearchInput(receipt, events, tuple(extraction.frames))
        self._ready[reservation.id] = result
        self._sizes[reservation.id] = estimate
        return result

    def release(self, reservation: InputReservation) -> None:
        if (
            reservation.id not in self._ready
            and self._reservations.get(reservation.id) == reservation
        ):
            self._reservations.pop(reservation.id, None)

    def read(self, actor: User, input_id: UUID) -> StoredResearchInput:
        self._expire()
        reservation = self._reservations.get(input_id)
        if (
            not actor.is_active
            or reservation is None
            or reservation.owner_id != actor.id
            or reservation.security_version != actor.security_version
            or input_id not in self._ready
        ):
            raise NotFound()
        return self._ready[input_id]
