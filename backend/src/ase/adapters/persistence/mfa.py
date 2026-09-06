"""MFA persistence with atomic single-use challenge transitions."""

from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.mfa_models import EmailMfaRow, MfaChallengeRow
from ase.domain.mfa import MfaChallenge, MfaPurpose


class SqlMfaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def email_enabled(self, user_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(EmailMfaRow.enabled).where(EmailMfaRow.user_id == user_id)
            )
        )

    async def set_email_enabled(self, user_id: UUID, enabled: bool) -> None:
        # Factor mutations hold the account lock in the application layer.
        row = await self._session.get(EmailMfaRow, user_id)
        if row is None:
            self._session.add(EmailMfaRow(user_id=user_id, enabled=enabled))
        else:
            row.enabled = enabled
        await self._session.flush()

    async def add(self, challenge: MfaChallenge) -> None:
        self._session.add(MfaChallengeRow(**asdict(challenge)))
        await self._session.flush()

    async def get(self, token_hash: str) -> MfaChallenge | None:
        row = await self._session.scalar(
            select(MfaChallengeRow)
            .where(MfaChallengeRow.token_hash == token_hash)
            .execution_options(populate_existing=True)
        )
        if row is None:
            return None
        return MfaChallenge(
            token_hash=row.token_hash,
            user_id=row.user_id,
            security_version=row.security_version,
            purpose=MfaPurpose(row.purpose),
            expires_at=row.expires_at,
            enrollment_required=row.enrollment_required,
            attempts=row.attempts,
            revision=row.revision,
            code_hash=row.code_hash,
            email_sent_at=row.email_sent_at,
            pending_encrypted=row.pending_encrypted,
            consumed_at=row.consumed_at,
        )

    async def save(self, challenge: MfaChallenge, expected_revision: int) -> bool:
        changed = await self._session.scalar(
            update(MfaChallengeRow)
            .where(
                MfaChallengeRow.token_hash == challenge.token_hash,
                MfaChallengeRow.revision == expected_revision,
                MfaChallengeRow.consumed_at.is_(None),
            )
            .values(
                attempts=challenge.attempts,
                revision=expected_revision + 1,
                code_hash=challenge.code_hash,
                email_sent_at=challenge.email_sent_at,
                pending_encrypted=challenge.pending_encrypted,
                consumed_at=challenge.consumed_at,
            )
            .returning(MfaChallengeRow.token_hash)
        )
        if changed is None:
            return False
        challenge.revision = expected_revision + 1
        return True
