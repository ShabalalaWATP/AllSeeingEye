"""Immutable edition comparison records pinned to exact report versions."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ase.domain.report_jobs import job_timestamp
from ase.domain.research_changes import ChangeClassification


@dataclass(frozen=True, slots=True)
class EditionComparison:
    edition_id: UUID
    previous_version_id: UUID | None
    current_version_id: UUID
    result: ChangeClassification
    created_at: datetime

    def __post_init__(self) -> None:
        if not all(isinstance(value, UUID) for value in (self.edition_id, self.current_version_id)):
            raise ValueError("Edition comparisons require exact saved identities.")
        if self.previous_version_id is not None and not isinstance(self.previous_version_id, UUID):
            raise ValueError("The comparison baseline identity is invalid.")
        if self.previous_version_id == self.current_version_id:
            raise ValueError("An edition cannot compare a report version with itself.")
        job_timestamp(self.created_at)
