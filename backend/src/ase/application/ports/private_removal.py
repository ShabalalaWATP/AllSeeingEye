"""Operator-only removal persistence, always inside the shared administration guard."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.private_removal import (
    NecessityReview,
    RemovalPlan,
    RemovalRequest,
    ReviewDecision,
    ReviewPurpose,
)


class PrivateRemovalRepository(Protocol):
    async def plan(self, request: RemovalRequest, now: datetime) -> RemovalPlan: ...

    async def remove(self, request: RemovalRequest, now: datetime) -> dict[str, int]: ...

    async def check_review_revision(self, owner_id: UUID, expected_revision: int) -> None: ...

    async def review(
        self,
        owner_id: UUID,
        actor_id: UUID,
        decision: ReviewDecision,
        purpose: ReviewPurpose,
        now: datetime,
        next_review_at: datetime,
        expected_revision: int,
    ) -> NecessityReview: ...
