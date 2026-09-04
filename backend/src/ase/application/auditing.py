"""Small helper so every use case records audit entries the same way."""

from __future__ import annotations

from uuid import UUID

from ase.application.ports import AuditLogRepository, Clock
from ase.domain.audit import AuditAction, AuditEntry


class Auditor:
    def __init__(self, repository: AuditLogRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def record(
        self,
        action: AuditAction,
        *,
        actor: UUID | None = None,
        subject: str | None = None,
        ip: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        entry = AuditEntry(
            at=self._clock.now(),
            action=action,
            actor_user_id=actor,
            subject=subject,
            ip=ip,
            details=details or {},
        )
        await self._repository.add(entry)
