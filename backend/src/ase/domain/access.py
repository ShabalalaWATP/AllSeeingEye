"""Current visibility supplied to storage queries before counting, sorting or limiting."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Visibility:
    user_id: UUID
    administrator: bool
    team_ids: tuple[UUID, ...]
