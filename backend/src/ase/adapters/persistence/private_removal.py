"""Transaction-scoped operator removal; no commits, external calls or implicit purge."""

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.private_removal_catalog import graph_inventory
from ase.adapters.persistence.private_removal_graph import collect_graph
from ase.adapters.persistence.private_removal_guards import execution_guards, logical_guards
from ase.adapters.persistence.private_removal_references import structured_guards
from ase.adapters.persistence.private_removal_selection import RemovalInventory
from ase.adapters.persistence.private_review_models import PrivateDataReviewRow
from ase.adapters.persistence.private_reviews import record_review, removal_review
from ase.adapters.persistence.session_changes import mark_session_change
from ase.domain.errors import Conflict, NotFound
from ase.domain.private_removal import (
    RETAINED_CATEGORIES,
    NecessityReview,
    RemovalPlan,
    RemovalRequest,
    RemovalScope,
    ReviewDecision,
    ReviewPurpose,
)


class SqlPrivateRemovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._prepared: tuple[RemovalRequest, RemovalInventory] | None = None

    async def review(
        self,
        owner_id: UUID,
        actor_id: UUID,
        decision: ReviewDecision,
        purpose: ReviewPurpose,
        now: datetime,
        next_review_at: datetime,
        expected_revision: int,
    ) -> NecessityReview:
        return await record_review(
            self.session,
            owner_id,
            actor_id,
            decision,
            purpose,
            now,
            next_review_at,
            expected_revision,
        )

    async def plan(self, request: RemovalRequest, now: datetime) -> RemovalPlan:
        self._prepared = None
        owner = await self.session.get(UserRow, request.owner_id, populate_existing=True)
        if owner is None:
            raise NotFound()
        graph = await collect_graph(self.session, request)
        inventory = graph_inventory(graph, request)
        inventory.blockers.update(graph.blockers)
        review, blockers = await removal_review(self.session, request.owner_id, now)
        inventory.blockers.update(blockers)
        if request.scope is RemovalScope.ACCOUNT:
            if owner.is_active:
                inventory.blockers.add("deactivate_account_first")
            if review and review.erased_at is not None:
                inventory.blockers.add("account_already_removed")
        await execution_guards(self.session, graph, inventory, request, now)
        await inventory.capture(self.session, request.owner_id)
        await inventory.check_foreign_references(self.session)
        await logical_guards(self.session, graph, inventory)
        await structured_guards(self.session, inventory)
        inventory.digest.update(
            json.dumps(
                {
                    "owner": str(request.owner_id),
                    "scope": request.scope.value,
                    "target": str(request.target_id),
                    "security_version": owner.security_version,
                    "active": owner.is_active,
                    "review_revision": review.revision if review else 0,
                    "blockers": sorted(inventory.blockers),
                },
                sort_keys=True,
            ).encode()
        )
        retained: tuple[str, ...] = (
            *RETAINED_CATEGORIES,
            "Unselected saved work, independent copies and historical account requests/enquiries.",
            "Research allowance history and operator evaluation runs/policy decisions.",
            "Unselected delivery receipts and unselected revoked-family replay markers.",
        )
        if request.scope is RemovalScope.JOB:
            retained += ("The job's final report remains unless selected separately.",)
        self._prepared = (request, inventory)
        return RemovalPlan(
            request,
            inventory.counts(),
            tuple(sorted(inventory.blockers)),
            retained,
            inventory.digest.hexdigest(),
            NecessityReview(
                review.owner_id,
                review.revision,
                ReviewDecision(review.decision),
                ReviewPurpose(review.purpose),
                review.reviewed_at,
                review.next_review_at,
                review.erased_at,
            )
            if review
            else None,
        )

    async def remove(self, request: RemovalRequest, now: datetime) -> dict[str, int]:
        if self._prepared is None or self._prepared[0] != request:
            raise Conflict("A fresh, locked removal preview is required.")
        inventory = self._prepared[1]
        self._prepared = None
        if inventory.blockers:
            raise Conflict("Removal is blocked.")
        await inventory.delete(self.session)
        if request.scope is RemovalScope.ACCOUNT:
            await self.session.execute(
                update(UserRow)
                .where(UserRow.id == request.owner_id)
                .values(
                    email=f"removed-{request.owner_id.hex}@invalid.example",
                    display_name="Removed account",
                    is_active=False,
                    password_hash=None,
                    role="user",
                    security_version=UserRow.security_version + 1,
                    failed_login_count=0,
                    last_failed_at=None,
                    locked_until=None,
                    last_login_at=None,
                )
                .execution_options(synchronize_session=False)
            )
            await self.session.execute(
                update(PrivateDataReviewRow)
                .where(PrivateDataReviewRow.owner_id == request.owner_id)
                .values(erased_at=now)
            )
            mark_session_change(self.session, request.owner_id)
        await self.session.flush()
        return inventory.counts()
