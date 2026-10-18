"""Fresh operator authority, review decisions and preview-bound private-data removal."""

import hmac
from datetime import timedelta
from uuid import UUID

from ase.application.admin.users import _lock_accounts
from ase.application.auditing import Auditor
from ase.application.ports import Clock, UnitOfWork, UserRepository
from ase.application.ports.private_removal import PrivateRemovalRepository
from ase.application.ports.recovery_journal import RecoveryJournal
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest
from ase.domain.private_removal import (
    NecessityReview,
    RemovalPlan,
    RemovalRequest,
    RemovalScope,
    ReviewDecision,
    ReviewPurpose,
)
from ase.domain.users import User


class PrivateRemovalService:
    def __init__(
        self,
        users: UserRepository,
        repository: PrivateRemovalRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        journal: RecoveryJournal | None = None,
    ) -> None:
        self.users, self.repository = users, repository
        self.clock, self.auditor, self.uow = clock, auditor, uow
        self.journal = journal

    async def preview(self, actor: User, request: RemovalRequest) -> RemovalPlan:
        await _lock_accounts(self.users, actor, request.owner_id)
        return await self.repository.plan(request, self.clock.now())

    async def apply(self, actor: User, request: RemovalRequest, fingerprint: str) -> dict[str, int]:
        await _lock_accounts(self.users, actor, request.owner_id)
        if request.scope is RemovalScope.ACCOUNT and actor.id == request.owner_id:
            raise Conflict("An operator cannot remove their own account.")
        now = self.clock.now()
        plan = await self.repository.plan(request, now)
        if plan.blockers:
            raise Conflict("Removal is blocked: " + ", ".join(plan.blockers))
        if (
            len(fingerprint) != 64
            or any(c not in "0123456789abcdef" for c in fingerprint)
            or not hmac.compare_digest(fingerprint, plan.fingerprint)
        ):
            raise Conflict("The removal preview changed. Review a fresh preview before applying.")
        intent = self.journal.begin_removal(actor.id, request, now) if self.journal else None
        counts = await self.repository.remove(request, now)
        await self.auditor.record(
            AuditAction.PRIVATE_DATA_REMOVED,
            actor=actor.id,
            subject=str(request.owner_id),
            details={
                "scope": request.scope.value,
                "target_id": str(request.target_id) if request.target_id else None,
                "fingerprint": fingerprint,
                "counts": counts,
            },
        )
        await self.uow.commit()
        self._complete(intent)
        return counts

    async def review(
        self,
        actor: User,
        owner_id: UUID,
        decision: ReviewDecision,
        purpose: ReviewPurpose,
        expected_revision: int,
        *,
        days: int = 90,
    ) -> NecessityReview:
        if not 1 <= days <= 90 or expected_revision < 0:
            raise InvalidRequest(
                "Use a non-negative revision and a review interval of 1 to 90 days."
            )
        await _lock_accounts(self.users, actor, owner_id)
        await self.repository.check_review_revision(owner_id, expected_revision)
        now = self.clock.now()
        intent = (
            self.journal.begin_review(
                actor.id,
                owner_id,
                decision,
                purpose,
                expected_revision + 1,
                now,
                now + timedelta(days=days),
            )
            if self.journal
            else None
        )
        review = await self.repository.review(
            owner_id,
            actor.id,
            decision,
            purpose,
            now,
            now + timedelta(days=days),
            expected_revision,
        )
        await self.auditor.record(
            AuditAction.PRIVATE_DATA_REVIEWED,
            actor=actor.id,
            subject=str(owner_id),
            details={
                "decision": decision.value,
                "purpose": purpose.value,
                "revision": review.revision,
                "next_review_at": review.next_review_at.isoformat(),
            },
        )
        await self.uow.commit()
        self._complete(intent)
        return review

    def _complete(self, intent: UUID | None) -> None:
        if self.journal and intent is not None:
            try:
                self.journal.complete(intent)
            except Exception:
                raise Conflict(
                    "The database committed, but journal completion is unconfirmed. "
                    "Keep recovery offline and investigate the pending intent before retrying."
                ) from None
