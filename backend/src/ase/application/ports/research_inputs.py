"""Private, transient extracted inputs, separated from parser and storage implementations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.events import Event
from ase.domain.users import User

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_INPUT_EVENTS = 200
MAX_INPUT_CHARACTERS = 200_000
INPUT_TTL_SECONDS = 15 * 60
MAX_PREVIEW_CHARACTERS = 1000
MAX_PREVIEW_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class InputPreviewFrame:
    seconds: float
    sha256: str
    png: bytes


@dataclass(frozen=True, slots=True)
class InputExtraction:
    filename: str
    media_type: str
    sha256: str
    events: tuple[Event, ...]
    limitations: tuple[str, ...]
    frames: tuple[InputPreviewFrame, ...] = ()
    parent_input_id: UUID | None = None
    parent_input_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class InputReservation:
    id: UUID
    owner_id: UUID
    security_version: int
    filename: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ResearchInputReceipt:
    id: UUID
    filename: str
    media_type: str
    sha256: str
    imported_at: datetime
    expires_at: datetime
    event_count: int
    extracted_characters: int
    preview: str
    limitations: tuple[str, ...]
    parent_input_id: UUID | None = None
    parent_input_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class StoredResearchInput:
    receipt: ResearchInputReceipt
    events: tuple[Event, ...]
    frames: tuple[InputPreviewFrame, ...] = ()


class DocumentImportPort(Protocol):
    async def extract(self, data: bytes, filename: str, captured_at: datetime) -> InputExtraction:
        """Use a bounded, killable parser; release raw bytes and resources on cancellation.

        Unsupported input raises InvalidRequest with a safe message. No original
        bytes, local paths or mutable parser objects may appear in the result.
        """
        ...


class ResearchInputStore(Protocol):
    def reserve(self, actor: User, filename: str) -> InputReservation: ...
    def require_pending(self, reservation: InputReservation) -> None: ...
    def put(
        self, reservation: InputReservation, extraction: InputExtraction
    ) -> StoredResearchInput: ...

    def release(self, reservation: InputReservation) -> None:
        """Release a pending reservation; successful extracted inputs remain until expiry."""
        ...

    def read(self, actor: User, input_id: UUID) -> StoredResearchInput:
        """Return only this current user's generation; expired/foreign ids raise NotFound."""
        ...

    def discard(self, actor: User, input_id: UUID) -> None:
        """Discard an owned working receipt and its derived receipts, never saved reports."""
        ...
