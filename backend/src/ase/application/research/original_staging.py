"""Expiring selected-original staging boundary for durable report jobs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.application.research.original_passages import OriginalDocumentVersion


@dataclass(frozen=True, slots=True)
class StagedOriginalPassage:
    id: UUID
    job_id: UUID
    event_id: str
    evidence_label: str
    document: OriginalDocumentVersion
    expires_at: datetime


class OriginalPassageStore(Protocol):
    async def stage(
        self,
        *,
        job_id: UUID,
        event_id: str,
        evidence_label: str,
        document: OriginalDocumentVersion,
    ) -> StagedOriginalPassage: ...

    async def staged(
        self, job_id: UUID, event_id: str, now: datetime
    ) -> StagedOriginalPassage | None: ...
