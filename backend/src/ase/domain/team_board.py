"""Small, plain-text team board records.

The board is deliberately separate from research evidence.  Posts are useful
working context, while reports and source records retain their own provenance
and access rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

MAX_POST_LENGTH = 4_000
MAX_REPLY_LENGTH = 2_000


def clean_text(value: str, *, reply: bool = False) -> str:
    """Bound a post and reject control characters that could become markup."""

    value = value.strip()
    maximum = MAX_REPLY_LENGTH if reply else MAX_POST_LENGTH
    if not value or len(value) > maximum:
        raise ValueError(f"Board text must contain 1 to {maximum} characters.")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError("Board text contains an unsupported control character.")
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


@dataclass(frozen=True, slots=True)
class TeamBoardPostView:
    post: TeamBoardPost
    author_name: str


@dataclass(frozen=True, slots=True)
class TeamBoardPage:
    items: tuple[TeamBoardPostView, ...]
    total: int
    offset: int
    limit: int

    @property
    def next_offset(self) -> int | None:
        next_value = self.offset + len(self.items)
        return next_value if next_value < self.total else None
