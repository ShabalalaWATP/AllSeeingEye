"""Compare-and-set necessity decisions; never silently release a preservation hold."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.private_review_models import PrivateDataReviewRow
from ase.domain.errors import Conflict
from ase.domain.private_removal import NecessityReview, ReviewDecision, ReviewPurpose


async def record_review(
    session: AsyncSession,
    owner_id: UUID,
    actor_id: UUID,
    decision: ReviewDecision,
    purpose: ReviewPurpose,
    now: datetime,
    next_review_at: datetime,
    expected_revision: int,
) -> NecessityReview:
    """The caller holds administration/account locks; audit and commit remain atomic."""
    row = await session.get(PrivateDataReviewRow, owner_id, populate_existing=True)
    if (row.revision if row else 0) != expected_revision:
        raise Conflict("The necessity review changed. Read its current revision before updating.")
    if row is None:
        row = PrivateDataReviewRow(owner_id=owner_id)
        session.add(row)
    row.revision = expected_revision + 1
    row.decision, row.purpose = decision.value, purpose.value
    row.reviewed_by, row.reviewed_at, row.next_review_at = actor_id, now, next_review_at
    # erased_at deliberately survives every future necessity/hold decision.
    await session.flush()
    return NecessityReview(
        owner_id, row.revision, decision, purpose, now, next_review_at, row.erased_at
    )


async def removal_review(
    session: AsyncSession,
    owner_id: UUID,
    now: datetime,
) -> tuple[PrivateDataReviewRow | None, tuple[str, ...]]:
    row = await session.get(PrivateDataReviewRow, owner_id, populate_existing=True)
    if row is None:
        return None, ("necessity_review_required",)
    if row.decision == ReviewDecision.HOLD:
        # A due review never releases a hold automatically.
        return row, ("preservation_hold",)
    if row.decision != ReviewDecision.REMOVE:
        return row, ("removal_not_authorised_by_review",)
    if row.next_review_at <= now:
        return row, ("necessity_review_due",)
    return row, ()
