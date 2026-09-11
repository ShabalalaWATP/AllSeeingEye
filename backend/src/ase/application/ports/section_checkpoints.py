"""Validated report steps retained by the job owner, never a shared response cache."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class SectionCheckpoint:
    status: Literal["running", "completed", "split", "incomplete"]
    payload: dict[str, Any] | None = None
    reason: str | None = None


class SectionCheckpoints(Protocol):
    async def load(self, packet_digest: str, section_id: str) -> SectionCheckpoint | None: ...
    async def save(
        self, packet_digest: str, section_id: str, checkpoint: SectionCheckpoint
    ) -> None: ...
