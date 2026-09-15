"""Bounded JSON contracts for the plain-text team board."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.team_board import TeamBoardPage, TeamBoardPost, TeamBoardPostView


class TeamBoardPostIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)
    parent_id: UUID | None = None


class TeamBoardPostUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)
    expected_revision: int = Field(ge=1)


class TeamBoardPinIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pinned: bool
    expected_revision: int = Field(ge=1)


class TeamBoardPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    author_id: UUID
    author_name: str
    text: str
    created_at: datetime
    updated_at: datetime
    parent_id: UUID | None
    is_pinned: bool
    deleted_at: datetime | None
    revision: int

    @classmethod
    def from_view(cls, view: TeamBoardPostView) -> Self:
        post = view.post
        return cls(
            id=post.id,
            team_id=post.team_id,
            author_id=post.author_id,
            author_name=view.author_name,
            text=post.text,
            created_at=post.created_at,
            updated_at=post.updated_at,
            parent_id=post.parent_id,
            is_pinned=post.is_pinned,
            deleted_at=post.deleted_at,
            revision=post.revision,
        )

    @classmethod
    def from_post(cls, post: TeamBoardPost, author_name: str) -> Self:
        return cls(
            id=post.id,
            team_id=post.team_id,
            author_id=post.author_id,
            author_name=author_name,
            text=post.text,
            created_at=post.created_at,
            updated_at=post.updated_at,
            parent_id=post.parent_id,
            is_pinned=post.is_pinned,
            deleted_at=post.deleted_at,
            revision=post.revision,
        )


class TeamBoardPageOut(BaseModel):
    items: list[TeamBoardPostOut]
    total: int
    offset: int
    limit: int
    next_offset: int | None

    @classmethod
    def from_page(cls, page: TeamBoardPage) -> Self:
        return cls(
            items=[TeamBoardPostOut.from_view(item) for item in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
            next_offset=page.next_offset,
        )
