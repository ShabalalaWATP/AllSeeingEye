"""In-app team invitations with explicit, auditable state transitions."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from ase.domain.errors import InvalidRequest
from ase.domain.teams import MembershipRole

MAX_INVITATION_NOTE = 280


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class TeamInvitation:
    id: UUID
    team_id: UUID
    recipient_id: UUID
    inviter_id: UUID
    role: MembershipRole
    note: str | None
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    responded_at: datetime | None = None
    revision: int = 1
    team_name: str | None = None
    inviter_display_name: str | None = None
    recipient_display_name: str | None = None
    recipient_username: str | None = None

    def __post_init__(self) -> None:
        if self.note is not None:
            note = self.note.strip()
            if not note or len(note) > MAX_INVITATION_NOTE:
                raise InvalidRequest(
                    f"Invitation notes must contain 1 to {MAX_INVITATION_NOTE} characters."
                )
            if any(ord(char) < 32 and char not in "\n\t" for char in note):
                raise InvalidRequest("Invitation notes contain an unsupported control character.")
            object.__setattr__(self, "note", note)
        if self.expires_at <= self.created_at:
            raise InvalidRequest("An invitation must expire after it is created.")
        if self.revision < 1:
            raise InvalidRequest("Invitation revisions start at one.")

    @property
    def is_pending(self) -> bool:
        return self.status is InvitationStatus.PENDING


@dataclass(frozen=True, slots=True)
class TeamInvitationPage:
    items: tuple[TeamInvitation, ...]
    total: int
    offset: int
    limit: int

    @property
    def next_offset(self) -> int | None:
        next_value = self.offset + len(self.items)
        return next_value if next_value < self.total else None
