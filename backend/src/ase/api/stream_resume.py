"""Stream positions: the SSE `id` a browser returns as Last-Event-ID to resume.

An id is `<epoch>-<sequence>`: the bus's random process epoch and the highest bus
sequence the stream has delivered or deliberately skipped (filtered events, denied
alerts and session signals). A browser holding it has every replayable public
message up to that sequence, so a resume replays only the later ones.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

MAX_EVENT_ID_LENGTH = 64
_EVENT_ID = re.compile(r"([0-9a-f]{1,32})-(0|[1-9][0-9]{0,17})")


@dataclass(frozen=True, slots=True)
class StreamPosition:
    epoch: str
    sequence: int


def parse_event_id(value: str | None) -> StreamPosition | None:
    """Validate an untrusted Last-Event-ID; anything malformed is simply not resumable."""
    if not value or len(value) > MAX_EVENT_ID_LENGTH:
        return None
    match = _EVENT_ID.fullmatch(value)
    if match is None:
        return None
    return StreamPosition(match[1], int(match[2]))


class StreamCursor:
    """Tracks a stream's position and stamps it on each frame it sends."""

    def __init__(self, epoch: str, position: int, now: datetime, interval: timedelta) -> None:
        self._epoch = epoch
        self.position = position
        self._sent = -1
        self._sent_at = now
        self._interval = interval

    @property
    def token(self) -> str:
        return f"{self._epoch}-{self.position}"

    def advance(self, sequence: int) -> None:
        self.position = max(self.position, sequence)

    def frame(self, event: str, data: str, now: datetime) -> dict[str, str]:
        self._sent, self._sent_at = self.position, now
        return {"event": event, "id": self.token, "data": data}

    def checkpoint(self, now: datetime, *, idle: bool) -> dict[str, str] | None:
        """An id-only frame when the position moved without a frame being sent.

        Browsers record the id without dispatching an event, so a narrowly filtered
        stream still resumes from a recent point rather than falling outside the
        replay window. Sent on an idle wake or at most once per interval.
        """
        if self.position == self._sent or (not idle and now - self._sent_at < self._interval):
            return None
        self._sent, self._sent_at = self.position, now
        return {"id": self.token}
