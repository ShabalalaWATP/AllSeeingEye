"""Explicit private conversation saves and current report-edition authorisation."""

from collections.abc import Iterable, Sequence
from uuid import UUID

from ase.application.ports.assistant_history import (
    AssistantHistoryRepository,
    SavedConversation,
    SavedConversationSummary,
)
from ase.application.ports.repositories import UnitOfWork
from ase.application.ports.services import Clock
from ase.application.reports.access import GetReportUseCase
from ase.domain.errors import NotFound
from ase.domain.users import User


class ManageAssistantHistory:
    def __init__(
        self,
        repository: AssistantHistoryRepository,
        reports: GetReportUseCase,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._repository, self._reports, self._clock, self._uow = repository, reports, clock, uow

    async def authorise_reports(self, actor: User, references: Iterable[tuple[UUID, int]]) -> None:
        for report_id, version in set(references):
            await self._reports.execute(actor, report_id, version)

    async def commit(self) -> None:
        """Caller checks response validation and session expiry before committing."""
        await self._uow.commit()

    async def list(self, actor: User) -> list[SavedConversationSummary]:
        return await self._repository.list(actor.id)

    async def get(self, actor: User, conversation_id: UUID) -> SavedConversation:
        record = await self._repository.get(actor.id, conversation_id)
        if record is None:
            raise NotFound()
        return record

    async def save(
        self,
        actor: User,
        title: str,
        turns: Sequence[dict[str, object]],
        references: Iterable[tuple[UUID, int]],
        conversation_id: UUID | None = None,
    ) -> SavedConversation:
        await self.authorise_reports(actor, references)
        if conversation_id is None:
            return await self._repository.create(actor.id, title, turns, self._clock.now())
        return await self._repository.update(
            actor.id, conversation_id, title, turns, self._clock.now()
        )

    async def remove(self, actor: User, conversation_id: UUID) -> None:
        if not await self._repository.remove(actor.id, conversation_id):
            raise NotFound()
