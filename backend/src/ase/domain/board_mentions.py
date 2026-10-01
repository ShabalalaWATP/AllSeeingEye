"""Plain-text @handle mentions on the team board and the notices they create.

A mention is parsed from the post text, resolved once against the team's current
roster and stored with the recipient's stable user id and the handle as written. Later
handle changes never redirect it. Text stays plain: nothing here produces markup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

MAX_MENTIONS: Final = 10
SNIPPET_LENGTH: Final = 160
# A handle as directory usernames allow it, not preceded by a word character or "@" (so
# an email address is not a mention) and not running on into a longer word.
_MENTION: Final = re.compile(r"(?<![A-Za-z0-9_@])@([A-Za-z0-9_]{3,32})(?![A-Za-z0-9_])")
TOO_MANY = f"A post can mention up to {MAX_MENTIONS} different teammates."


def mentioned_handles(text: str) -> tuple[str, ...]:
    """Distinct lowercase handles in first-seen order; more than the cap is refused."""
    handles = tuple(dict.fromkeys(match.lower() for match in _MENTION.findall(text)))
    if len(handles) > MAX_MENTIONS:
        raise ValueError(TOO_MANY)
    return handles


def snippet(text: str) -> str:
    """A single-line, bounded plain-text excerpt of a post."""
    flat = " ".join(text.split())
    return flat if len(flat) <= SNIPPET_LENGTH else f"{flat[: SNIPPET_LENGTH - 1].rstrip()}…"


@dataclass(frozen=True, slots=True)
class Mentioned:
    """A teammate a write newly notified, as the author may already see them in the roster."""

    user_id: UUID
    display_name: str


@dataclass(frozen=True, slots=True)
class MentionNotice:
    """What a recipient may see of a mention while they can still read the post."""

    post_id: UUID
    thread_id: UUID
    team_id: UUID
    team_name: str
    author_name: str
    snippet: str
    created_at: datetime
    read_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MentionSection:
    items: tuple[MentionNotice, ...]
    unread: int
    muted: bool
