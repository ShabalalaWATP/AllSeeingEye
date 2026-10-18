"""External decision evidence, deliberately outside the database being restored."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.private_removal import RemovalRequest, ReviewDecision, ReviewPurpose


class RecoveryJournal(Protocol):
    def begin_removal(self, actor: UUID, request: RemovalRequest, now: datetime) -> UUID: ...

    def begin_review(
        self,
        actor: UUID,
        owner: UUID,
        decision: ReviewDecision,
        purpose: ReviewPurpose,
        revision: int,
        now: datetime,
        due: datetime,
    ) -> UUID: ...

    def complete(self, event: UUID) -> None: ...
