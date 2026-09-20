"""Coordinate saved-profile removal with allowance admission inside a transaction."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import LlmProfileRow


async def lock_profile_reference(
    session: AsyncSession, profile_id: UUID, *, for_delete: bool = False
) -> UUID | None:
    """Lock before ledger/policy writes; return no reference for a removed profile."""
    query = select(LlmProfileRow.id).where(LlmProfileRow.id == profile_id)
    if session.get_bind().dialect.name == "sqlite":
        # SQLite ignores FOR UPDATE. Acquire its writer lock before reading so
        # another connection cannot remove the profile before reservation insert.
        await session.execute(
            update(LlmProfileRow).where(LlmProfileRow.id == profile_id).values(id=LlmProfileRow.id)
        )
    else:
        query = query.with_for_update(read=not for_delete, key_share=not for_delete)
    locked_id: UUID | None = await session.scalar(query)
    return locked_id
