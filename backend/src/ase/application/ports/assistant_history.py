"""Owner-scoped conversation snapshots, independent of ORM and HTTP models."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SavedConversationSummary:
    id: UUID
    title: str
    turn_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SavedConversation:
    id: UUID
    title: str
    turns: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class AssistantHistoryRepository(Protocol):
    async def list(self, owner_id: UUID) -> list[SavedConversationSummary]: ...
    async def get(self, owner_id: UUID, conversation_id: UUID) -> SavedConversation | None: ...
    async def remove(self, owner_id: UUID, conversation_id: UUID) -> bool: ...
    async def create(
        self, owner_id: UUID, title: str, turns: Sequence[dict[str, object]], now: datetime
    ) -> SavedConversation: ...
    async def update(
        self,
        owner_id: UUID,
        conversation_id: UUID,
        title: str,
        turns: Sequence[dict[str, object]],
        now: datetime,
    ) -> SavedConversation: ...
