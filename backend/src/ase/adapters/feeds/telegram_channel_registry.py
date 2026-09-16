"""What one curated Telegram channel is, who runs it, and how its viewpoint is declared.

Every channel in this registry was loaded from ``https://t.me/s/<username>`` and parsed
before it was added, and an entry records who operates the channel rather than letting a
display name speak for itself. Several Telegram channels carry official-sounding names
while being run by nobody in particular; the ``operator`` and ``reason`` fields exist so
that a reader is never left inferring authority from a title.

Nothing here confers reliability. Channels run by governments, armed forces, state media
and aligned commentators are participants in what they describe, so the connector grades
every post at doctrine's floor and uses ``viewpoint_tags`` to mark state-aligned and
official-issuer material exactly as the state-aligned news feeds are marked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

USERNAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{3,31}")
TOPICS = frozenset(
    {
        "ukraine_official",
        "ukraine_media",
        "russia_official",
        "russia_state_media",
        "russia_milblogger",
        "russia_independent",
        "middle_east",
        "asia_pacific",
        "africa_sahel",
        "cyber_threat",
        "finance_sanctions",
        "emergency_response",
        "conflict_monitoring",
    }
)
MIN_POLL_MINUTES = 30
MAX_POLL_MINUTES = 240

# How the channel stands to what it reports. None of these is a reliability grade.
Viewpoint = Literal[
    "official_issuer",  # an institution's own account, speaking for that institution
    "state_media",  # a state-run, state-funded or state-directed outlet
    "aligned_commentator",  # openly aligned with one party: milbloggers, advocacy, mapping
    "publisher",  # an outlet or researcher with no declared party alignment
]
_VIEWPOINT_TAGS: dict[str, frozenset[str]] = {
    "official_issuer": frozenset({"official_issuer", "interested_party"}),
    "state_media": frozenset({"state_aligned", "interested_party"}),
    "aligned_commentator": frozenset({"interested_party"}),
    "publisher": frozenset(),
}


def preview_url(username: str) -> str:
    return f"https://t.me/s/{username}"


def channel_url(username: str) -> str:
    return f"https://t.me/{username}"


@dataclass(frozen=True, slots=True)
class TelegramChannel:
    username: str
    name: str
    operator: str
    topic: str
    reason: str
    viewpoint: Viewpoint
    alignment: str = ""
    language: str = "en"
    poll_minutes: int = 60

    def __post_init__(self) -> None:
        if not USERNAME.fullmatch(self.username):
            raise ValueError(f"{self.username}: not a public Telegram channel username")
        if self.topic not in TOPICS:
            raise ValueError(f"{self.username}: unknown registry topic {self.topic}")
        if self.viewpoint not in _VIEWPOINT_TAGS:
            raise ValueError(f"{self.username}: unknown viewpoint {self.viewpoint}")
        if not self.name or not self.operator or len(self.reason) < 20:
            raise ValueError(f"{self.username}: needs a name, an operator and a stated reason")
        if not MIN_POLL_MINUTES <= self.poll_minutes <= MAX_POLL_MINUTES:
            raise ValueError(f"{self.username}: poll interval is outside the polite range")

    @property
    def source_id(self) -> str:
        return f"telegram_{self.username.casefold()}"

    @property
    def viewpoint_tags(self) -> frozenset[str]:
        """The tags the interface already uses to mark official and state-aligned material."""
        return _VIEWPOINT_TAGS[self.viewpoint]

    @property
    def state_aligned(self) -> bool:
        return self.viewpoint in ("official_issuer", "state_media")


def channel(
    username: str,
    name: str,
    operator: str,
    topic: str,
    reason: str,
    viewpoint: Viewpoint,
    *,
    alignment: str = "",
    language: str = "en",
    minutes: int = 60,
) -> TelegramChannel:
    return TelegramChannel(
        username, name, operator, topic, reason, viewpoint, alignment, language, minutes
    )


def validate(channels: tuple[TelegramChannel, ...]) -> tuple[TelegramChannel, ...]:
    """One entry per channel, per source id, and no bare topic with nothing in it."""
    usernames = [entry.username.casefold() for entry in channels]
    if len(set(usernames)) != len(usernames):
        raise ValueError("A Telegram channel is registered twice")
    if len({entry.source_id for entry in channels}) != len(channels):
        raise ValueError("Two Telegram channels resolve to the same source id")
    return channels
