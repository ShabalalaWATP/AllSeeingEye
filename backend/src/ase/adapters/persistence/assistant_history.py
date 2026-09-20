"""Owner-scoped persistence for explicitly saved Ask Eye transcripts."""

import json
from collections.abc import Sequence
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.assistant_history_models import AssistantConversationRow
from ase.adapters.persistence.models import UserRow
from ase.application.assistant_history.service import encode_transcript, require_capacity
from ase.application.ports.assistant_history import SavedConversation, SavedConversationSummary
from ase.domain.errors import NotFound


def _record(row: AssistantConversationRow) -> SavedConversation:
    turns = json.loads(row.transcript)["turns"]
    for turn in turns:
        # Never restore transient continuation authority or private model details.
        turn["answer"]["continuation_id"] = None
        turn["answer"]["model"] = None
    return SavedConversation(row.id, row.title, turns, row.created_at, row.updated_at)


class SqlAssistantHistory:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_owner(self, owner_id: UUID) -> None:
        # Serialises per-owner quota checks on PostgreSQL. Authentication and
        # deactivation are rechecked by the route immediately before commit.
        await self.session.scalar(
            select(UserRow.id).where(UserRow.id == owner_id).with_for_update()
        )

    async def count(self, owner_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(AssistantConversationRow)
                .where(AssistantConversationRow.owner_id == owner_id)
            )
            or 0
        )

    async def list(self, owner_id: UUID) -> list[SavedConversationSummary]:
        rows = list(
            await self.session.scalars(
                select(AssistantConversationRow)
                .where(AssistantConversationRow.owner_id == owner_id)
                .order_by(AssistantConversationRow.updated_at.desc(), AssistantConversationRow.id)
                .limit(30)
            )
        )

        return [
            SavedConversationSummary(
                row.id, row.title, row.turn_count, row.created_at, row.updated_at
            )
            for row in rows
        ]

    async def get(self, owner_id: UUID, conversation_id: UUID) -> SavedConversation | None:
        row = await self._row(owner_id, conversation_id)
        return _record(row) if row is not None else None

    async def _row(self, owner_id: UUID, conversation_id: UUID) -> AssistantConversationRow | None:
        return cast(
            AssistantConversationRow | None,
            await self.session.scalar(
                select(AssistantConversationRow)
                .where(
                    AssistantConversationRow.owner_id == owner_id,
                    AssistantConversationRow.id == conversation_id,
                )
                .execution_options(populate_existing=True)
            ),
        )

    async def remove(self, owner_id: UUID, conversation_id: UUID) -> bool:
        row = await self._row(owner_id, conversation_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def create(
        self, owner_id: UUID, title: str, turns: Sequence[dict[str, object]], now: datetime
    ) -> SavedConversation:
        transcript, size = encode_transcript(turns)
        await self.lock_owner(owner_id)
        require_capacity(await self.count(owner_id))
        row = AssistantConversationRow(
            id=uuid4(),
            owner_id=owner_id,
            title=title.strip(),
            transcript=transcript,
            transcript_bytes=size,
            turn_count=len(turns),
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        await self.session.flush()
        return _record(row)

    async def update(
        self,
        owner_id: UUID,
        conversation_id: UUID,
        title: str,
        turns: Sequence[dict[str, object]],
        now: datetime,
    ) -> SavedConversation:
        transcript, size = encode_transcript(turns)
        row = await self._row(owner_id, conversation_id)
        if row is None:
            raise NotFound()
        row.title = title.strip()
        row.transcript = transcript
        row.transcript_bytes = size
        row.turn_count = len(turns)
        row.updated_at = now
        await self.session.flush()
        return _record(row)
