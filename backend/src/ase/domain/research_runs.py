"""Small, ephemeral progress records with no research text or source material."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ResearchStage(StrEnum):
    PLANNING = "planning"
    COLLECTING = "collecting"
    DRAFTING = "drafting"
    CHALLENGING = "challenging"
    VALIDATING = "validating"
    SAVING = "saving"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    TIMED_OUT = "timed_out"

    @property
    def terminal(self) -> bool:
        return self in {self.COMPLETED, self.CANCELLED, self.FAILED, self.TIMED_OUT}


@dataclass(frozen=True, slots=True)
class ResearchRun:
    id: UUID
    owner_id: UUID
    security_version: int
    stage: ResearchStage
    started_at: datetime
    updated_at: datetime
    expires_at: datetime
    report_id: UUID | None = None
