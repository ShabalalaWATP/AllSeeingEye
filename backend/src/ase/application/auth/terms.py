"""Whether an account must accept the current Terms, and recording that acceptance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.domain.audit import AuditAction
from ase.domain.terms import CURRENT_TERMS_VERSION, TermsVersionChanged
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class TermsStatus:
    current_version: str
    accepted_version: str | None
    accepted_at: datetime | None
    acceptance_required: bool


def terms_status(user: User) -> TermsStatus:
    """Accounts that never accepted, or accepted an earlier version, must accept again."""
    return TermsStatus(
        current_version=CURRENT_TERMS_VERSION,
        accepted_version=user.terms_version,
        accepted_at=user.terms_accepted_at,
        acceptance_required=user.terms_version != CURRENT_TERMS_VERSION,
    )


class AcceptTermsUseCase:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def execute(
        self, claims: AccessClaims, version: str, context: RequestContext
    ) -> TermsStatus:
        # The reader accepts the version they were shown; a newer one needs a fresh review.
        if version != CURRENT_TERMS_VERSION:
            raise TermsVersionChanged()
        # Follow administrative lock ordering, then reload the identity, so this write
        # never overwrites a concurrent role, credential or status change.
        await self._users.lock_administration()
        await self._users.lock_by_id(claims.user_id)
        current = await validate_current_session(
            claims, self._users, self._refresh_tokens, self._clock
        )
        if current.terms_version == CURRENT_TERMS_VERSION:
            # Repeats keep the original acceptance time and add no audit entry.
            await self._uow.rollback()
            return terms_status(current)
        previous = current.terms_version
        current.terms_version = CURRENT_TERMS_VERSION
        current.terms_accepted_at = self._clock.now()
        await self._users.save(current)
        await self._auditor.record(
            AuditAction.TERMS_ACCEPTED,
            actor=current.id,
            subject=str(current.id),
            ip=context.ip,
            details={"terms_version": CURRENT_TERMS_VERSION, "previous_version": previous},
        )
        await self._uow.commit()
        return terms_status(current)
