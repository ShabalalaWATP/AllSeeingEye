"""What one watched YouTube channel is, how it is graded and how far it may be read.

The reviewed rows themselves are in `youtube_channel_seeds.py`. The channel Atom feeds
this application used to poll live under `/feeds/videos.xml`, which
`https://www.youtube.com/robots.txt` disallows for `User-agent: *` (checked 16
September 2026), so the only compliant route is the official API with an operator key.
Nothing is collected without one.

Grades follow the same rule as the RSS catalogue. An outlet's video carries that
outlet's reliability, because it is the outlet's own report. An independent analysis
channel sits at doctrine's floor (E, credibility 6) until something corroborates it.
An official body's channel is graded as its other official publications are (B,
credibility 2). A state-run broadcaster is tagged `state_controlled` and treated as
the government's position, exactly as `rss_seeds.STATE_MEDIA` does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from ase.domain.events import Credibility, Reliability

MAX_CHANNELS = 48
MIN_POLL_MINUTES = 15
MAX_POLL_MINUTES = 360
DEFAULT_POLL_MINUTES = 30
# One request start per second, so a restart cannot burst one project quota.
HOST_REQUEST_SPACING_SECONDS = 1.0
CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
UPLOADS_ID = re.compile(r"^UU[A-Za-z0-9_-]{22}$")
_HANDLE = re.compile(r"^@[A-Za-z0-9._-]{3,29}$")
_SOURCE_ID = re.compile(r"^yt_[a-z0-9_]{2,40}$")
TOPICS = frozenset(
    {
        "china",
        "cyber",
        "defence_analysis",
        "drones",
        "finance",
        "middle_east",
        "official",
        "russia",
        "taiwan",
        "ukraine",
        "world_news",
    }
)
ChannelKind = Literal["outlet", "analysis", "official"]
_CREDIBILITY: dict[ChannelKind, Credibility] = {
    "outlet": Credibility.POSSIBLY_TRUE,
    "analysis": Credibility.CANNOT_BE_JUDGED,
    "official": Credibility.PROBABLY_TRUE,
}
_RATIONALE: dict[ChannelKind, str] = {
    "outlet": "Outlet video report, not yet corroborated",
    "analysis": "Independent analysis channel; not corroborated",
    "official": "Official publication on the issuing body's own channel",
}
STATE_RATIONALE = "State-controlled outlet; treat as the government's position"


@dataclass(frozen=True, slots=True)
class YouTubeChannel:
    """One reviewed channel, how it is graded and how often it is read."""

    source_id: str
    name: str
    organisation: str
    handle: str
    topics: tuple[str, ...]
    reliability: Reliability
    kind: ChannelKind = "outlet"
    channel_id: str = ""
    state_aligned: bool = False
    language: str = "en"
    minutes: int = DEFAULT_POLL_MINUTES

    def __post_init__(self) -> None:
        if not _SOURCE_ID.fullmatch(self.source_id) or len(self.name) > 120:
            raise ValueError(f"Unsupported YouTube channel identity: {self.source_id!r}")
        if not _HANDLE.fullmatch(self.handle):
            raise ValueError(f"Unsupported YouTube handle: {self.handle!r}")
        if self.channel_id and not CHANNEL_ID.fullmatch(self.channel_id):
            raise ValueError(f"Unsupported YouTube channel ID: {self.channel_id!r}")
        if not self.topics or not set(self.topics) <= TOPICS:
            raise ValueError(f"Unreviewed YouTube topic on {self.source_id}")
        if not MIN_POLL_MINUTES <= self.minutes <= MAX_POLL_MINUTES:
            raise ValueError(
                f"Poll interval must be {MIN_POLL_MINUTES} to {MAX_POLL_MINUTES} minutes"
            )
        if self.state_aligned and self.kind != "outlet":
            raise ValueError("A state-aligned channel is graded as an outlet")

    @property
    def credibility(self) -> Credibility:
        return Credibility.DOUBTFUL if self.state_aligned else _CREDIBILITY[self.kind]

    @property
    def rationale(self) -> str:
        return STATE_RATIONALE if self.state_aligned else _RATIONALE[self.kind]

    @property
    def tags(self) -> frozenset[str]:
        extra = {"state_controlled"} if self.state_aligned else set()
        if self.kind == "official":
            extra.add("official")
        return frozenset({"youtube", *self.topics, *extra})


def channel(
    source_id: str,
    name: str,
    organisation: str,
    handle: str,
    topics: str,
    reliability: Reliability,
    **extra: object,
) -> YouTubeChannel:
    return YouTubeChannel(
        source_id,
        name,
        organisation,
        handle,
        tuple(topics.split()),
        reliability,
        **extra,  # type: ignore[arg-type]
    )


def channel_host_intervals() -> dict[str, float]:
    """Request spacing for the shared host pacer; every channel uses one API host."""
    return {"www.googleapis.com": HOST_REQUEST_SPACING_SECONDS}
