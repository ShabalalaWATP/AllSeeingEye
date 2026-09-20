"""Read only the expiring excerpt linked to an exact saved report edition."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.application.research.original_staging import StagedOriginalPassage


class LinkedOriginalPassages(Protocol):
    async def linked(
        self, ref: UUID, version_id: UUID, now: datetime
    ) -> StagedOriginalPassage | None: ...
