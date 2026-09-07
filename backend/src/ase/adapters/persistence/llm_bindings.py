"""Exact-scope AI connection bindings, changed under the administration guard."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.domain.llm import LlmConnectionBinding


class LlmBindingSequenceRow(Base):
    """A single durable counter prevents stale confirmations surviving scope reset."""

    __tablename__ = "llm_binding_sequence"
    __table_args__ = (CheckConstraint("id = 1", name="ck_llm_binding_sequence_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


class LlmConnectionBindingRow(Base):
    __tablename__ = "llm_connection_bindings"
    __table_args__ = (
        CheckConstraint(
            "(team_id IS NULL AND user_id IS NULL AND scope_key = 'global') OR "
            "(team_id IS NOT NULL AND user_id IS NULL AND scope_key LIKE 'team:%') OR "
            "(team_id IS NULL AND user_id IS NOT NULL AND scope_key LIKE 'user:%')",
            name="ck_llm_binding_scope",
        ),
    )

    scope_key: Mapped[str] = mapped_column(String(48), primary_key=True)
    team_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_llm_binding_user"),
        nullable=True,
        unique=True,
    )
    profile_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("llm_profiles.id", ondelete="RESTRICT"), index=True
    )
    profile_revision: Mapped[int] = mapped_column(Integer)
    tested_config_hash: Mapped[str] = mapped_column(String(64))
    activated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    activated_by: Mapped[UUID] = mapped_column(Uuid)
    revision: Mapped[int] = mapped_column(Integer)


def _key(team_id: UUID | None, user_id: UUID | None = None) -> str:
    if user_id is not None:
        if team_id is not None:
            raise ValueError("An AI connection has exactly one audience.")
        return f"user:{user_id}"
    return f"team:{team_id}" if team_id is not None else "global"


def _domain(row: LlmConnectionBindingRow) -> LlmConnectionBinding:
    return LlmConnectionBinding(
        row.team_id,
        row.profile_id,
        row.profile_revision,
        row.tested_config_hash,
        row.activated_at,
        row.activated_by,
        row.revision,
        row.user_id,
    )


class SqlLlmBindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_revision(self) -> int:
        # All callers hold the administration guard until the binding and audit commit.
        row = await self._session.get(LlmBindingSequenceRow, 1, populate_existing=True)
        if row is None:
            row = LlmBindingSequenceRow(id=1, value=0)
            self._session.add(row)
        row.value += 1
        await self._session.flush()
        return row.value

    async def get(
        self, team_id: UUID | None, *, user_id: UUID | None = None
    ) -> LlmConnectionBinding | None:
        row = await self._session.get(
            LlmConnectionBindingRow, _key(team_id, user_id), populate_existing=True
        )
        return _domain(row) if row else None

    async def list_all(self) -> list[LlmConnectionBinding]:
        rows = await self._session.scalars(
            select(LlmConnectionBindingRow).order_by(LlmConnectionBindingRow.scope_key)
        )
        return [_domain(row) for row in rows]

    async def save(self, binding: LlmConnectionBinding) -> None:
        row = await self._session.get(
            LlmConnectionBindingRow, _key(binding.team_id, binding.user_id)
        )
        if row is None:
            row = LlmConnectionBindingRow(scope_key=_key(binding.team_id, binding.user_id))
            self._session.add(row)
        row.user_id = binding.user_id
        row.team_id = binding.team_id
        row.profile_id = binding.profile_id
        row.profile_revision = binding.profile_revision
        row.tested_config_hash = binding.tested_config_hash
        row.activated_at = binding.activated_at
        row.activated_by = binding.activated_by
        row.revision = binding.revision
        await self._session.flush()

    async def delete(self, team_id: UUID | None, *, user_id: UUID | None = None) -> None:
        await self._session.execute(
            delete(LlmConnectionBindingRow).where(
                LlmConnectionBindingRow.scope_key == _key(team_id, user_id)
            )
        )

    async def is_bound(self, profile_id: UUID) -> bool:
        return (
            await self._session.scalar(
                select(LlmConnectionBindingRow.scope_key)
                .where(LlmConnectionBindingRow.profile_id == profile_id)
                .limit(1)
            )
            is not None
        )
