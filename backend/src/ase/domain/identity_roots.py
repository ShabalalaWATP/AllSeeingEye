"""Access scope and immutable report anchor for retained identity decision history."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IdentityDecisionRoot:
    id: UUID
    report_id: UUID
    report_version_id: UUID
    report_version_number: int
    created_by: UUID
    team_id: UUID | None
    subject: str
    candidate_label: str
    evidence_sha256: str
    latest_revision_id: UUID
    created_at: datetime
