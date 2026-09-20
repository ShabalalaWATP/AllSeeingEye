"""Strict envelopes for versioned, user-authored map artefacts."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.map_workspace import WorkspaceKind


class MapWorkspaceCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: WorkspaceKind
    title: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any]
    team_id: UUID | None = None


class MapWorkspaceUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any]
    expected_revision: int = Field(ge=1, strict=True)


class MapWorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: WorkspaceKind
    title: str
    payload: dict[str, Any]
    revision: int
    created_by: UUID
    team_id: UUID | None
    created_at: datetime
    updated_at: datetime
