"""Account-owned refresh-family management boundary."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.session_summary import SessionPage


class AccountSessionRepository(Protocol):
    async def list_active(
        self, user_id: UUID, current_family: UUID, now: datetime
    ) -> SessionPage: ...

    async def owns_family(self, user_id: UUID, family_id: UUID) -> bool: ...

    async def revoke_others(self, user_id: UUID, current_family: UUID, now: datetime) -> None: ...
