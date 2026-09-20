"""Scoped brief management without exposing persistence rows or transport models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_values import BriefIdentity


@dataclass(frozen=True, slots=True)
class BriefSummary:
    id: UUID
    revision: int
    owner_id: UUID
    team_id: UUID | None
    title: str
    schema_version: int
    origin: str
    published: bool
    created_at: datetime
    revised_at: datetime


class BriefDraft(Protocol):
    """A validated definition that can be bound to a server-owned identity."""

    @property
    def title(self) -> str: ...
    @property
    def team_id(self) -> UUID | None: ...
    @property
    def preset_id(self) -> str | None: ...
    @property
    def preset_version(self) -> int | None: ...
    def to_brief(self, identity: BriefIdentity) -> ResearchBrief: ...


class BriefManagementRepository(Protocol):
    async def visible(
        self, visibility: Visibility, brief_id: UUID, revision: int | None = None
    ) -> ResearchBrief | None: ...

    async def list_visible(
        self, visibility: Visibility, limit: int, offset: int, brief_id: UUID | None = None
    ) -> list[BriefSummary]:
        """Apply visibility before pagination; list latest revisions unless a brief is given."""
        ...

    async def add_revision(
        self, brief: ResearchBrief, *, actor_id: UUID, authorised_team_ids: tuple[UUID, ...] = ()
    ) -> ResearchBrief: ...
