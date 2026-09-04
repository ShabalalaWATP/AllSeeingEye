"""Paginated audit log for administrators."""

from __future__ import annotations

from ase.application.dto import AuditPage
from ase.application.policy import require_admin
from ase.application.ports import AuditLogRepository
from ase.domain.users import User

MAX_PAGE = 200


class ListAuditUseCase:
    def __init__(self, audit: AuditLogRepository) -> None:
        self._audit = audit

    async def execute(self, actor: User, before: int | None, limit: int) -> AuditPage:
        require_admin(actor)
        limit = max(1, min(limit, MAX_PAGE))
        items = await self._audit.list_before(before, limit)
        last_id = items[-1].id if len(items) == limit else None
        return AuditPage(items=items, next_before=last_id)
