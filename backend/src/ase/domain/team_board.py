"""Small, plain-text team board records.

The board is deliberately separate from research evidence.  Posts are useful
working context, while reports and source records retain their own provenance
and access rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

MAX_POST_LENGTH = 4_000
MAX_REPLY_LENGTH = 2_000
MAX_PINNED_POSTS = 3
MAX_PAGE_SIZE = 20
MAX_REPLIES_PER_POST = 50
UNREAD_COUNT_CAP = 100
MIN_REASON_LENGTH = 3
MAX_REASON_LENGTH = 300

AUTHOR_TOMBSTONE = "[Removed by author]"
MODERATOR_TOMBSTONE = "[Removed by a moderator]"


class BoardRemoval(StrEnum):
    AUTHOR = "author"
    MODERATOR = "moderator"


def _reject_controls(value: str, message: str) -> None:
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError(message)


def clean_text(value: str, *, reply: bool = False) -> str:
    """Bound a post and reject control characters that could become markup."""

    value = value.strip()
    maximum = MAX_REPLY_LENGTH if reply else MAX_POST_LENGTH
    if not value or len(value) > maximum:
        raise ValueError(f"Board text must contain 1 to {maximum} characters.")
    _reject_controls(value, "Board text contains an unsupported control character.")
    return value


def clean_reason(value: str | None) -> str:
    """A moderation reason is kept for the audit trail, never shown on the board."""

    value = (value or "").strip()
    if not MIN_REASON_LENGTH <= len(value) <= MAX_REASON_LENGTH:
        raise ValueError(
            f"A moderation reason must contain {MIN_REASON_LENGTH} to "
            f"{MAX_REASON_LENGTH} characters."
        )
    if "\n" in value or "\t" in value:
        raise ValueError("A moderation reason must be a single line.")
    _reject_controls(value, "The moderation reason contains an unsupported control character.")
    return value


@dataclass(frozen=True, slots=True)
class TeamBoardPost:
    id: UUID
    team_id: UUID
    author_id: UUID
    text: str
    created_at: datetime
    updated_at: datetime
    parent_id: UUID | None = None
    is_pinned: bool = False
    deleted_at: datetime | None = None
    revision: int = 1
    edited_at: datetime | None = None
    removal: BoardRemoval | None = None


@dataclass(frozen=True, slots=True)
class TeamBoardPostView:
    post: TeamBoardPost
    author_name: str


@dataclass(frozen=True, slots=True)
class TeamBoardPage:
    """A page of top-level posts plus the bounded replies to those posts."""

    items: tuple[TeamBoardPostView, ...]
    replies: tuple[TeamBoardPostView, ...]
    total: int
    offset: int
    limit: int
    unread_count: int = 0

    @property
    def next_offset(self) -> int | None:
        next_value = self.offset + len(self.items)
        return next_value if next_value < self.total else None


@dataclass(frozen=True, slots=True)
class TeamBoardReadCursor:
    """What one membership has seen.

    ``membership_joined_at`` ties the cursor to one membership: after removal and
    re-admission the join time differs, so an old cursor is ignored.  It is None
    for an administrator reading a team without membership.
    """

    team_id: UUID
    user_id: UUID
    membership_joined_at: datetime | None
    last_read_at: datetime
    last_read_post_id: UUID
    updated_at: datetime
