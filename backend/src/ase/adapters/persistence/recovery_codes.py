"""Conditional deletion consumes a recovery code in the session transaction."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.recovery_models import RecoveryCodeRow


class SqlRecoveryCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count(self, user_id: UUID, security_version: int) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(RecoveryCodeRow)
                .where(
                    RecoveryCodeRow.user_id == user_id,
                    RecoveryCodeRow.security_version == security_version,
                )
            )
            or 0
        )

    async def clear(self, user_id: UUID) -> None:
        await self.session.execute(
            delete(RecoveryCodeRow).where(RecoveryCodeRow.user_id == user_id)
        )

    async def replace(self, user_id: UUID, security_version: int, hashes: list[str]) -> None:
        await self.clear(user_id)
        self.session.add_all(
            [
                RecoveryCodeRow(user_id=user_id, security_version=security_version, code_hash=value)
                for value in hashes
            ]
        )
        await self.session.flush()

    async def consume(self, user_id: UUID, security_version: int, code_hash: str) -> bool:
        result = await self.session.execute(
            delete(RecoveryCodeRow)
            .where(
                RecoveryCodeRow.user_id == user_id,
                RecoveryCodeRow.security_version == security_version,
                RecoveryCodeRow.code_hash == code_hash,
            )
            .returning(RecoveryCodeRow.code_hash)
        )
        return result.scalar_one_or_none() is not None
