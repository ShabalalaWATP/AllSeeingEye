"""Bounded JSON contracts for the plain-text team board."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.team_board import (
    MAX_REASON_LENGTH,
    TeamBoardPage,
    TeamBoardPost,
    TeamBoardPostView,
)


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
    reason: str | None = Field(default=None, max_length=MAX_REASON_LENGTH)


class TeamBoardRemoveIn(BaseModel):
    """Moderators must give a reason for removing someone else's post; it is audited only."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=MAX_REASON_LENGTH)


class TeamBoardReadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_seen_post_id: UUID


class TeamBoardUnreadOut(BaseModel):
    unread_count: int


class TeamBoardPostOut(BaseModel):
    id: UUID
    team_id: UUID
    author_id: UUID
    author_name: str
    text: str
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None
    parent_id: UUID | None
    is_pinned: bool
    deleted_at: datetime | None
    removal: Literal["author", "moderator"] | None
    revision: int

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
            edited_at=post.edited_at,
            parent_id=post.parent_id,
            is_pinned=post.is_pinned,
            deleted_at=post.deleted_at,
            removal=post.removal.value if post.removal else None,
            revision=post.revision,
        )

    @classmethod
    def from_view(cls, view: TeamBoardPostView) -> Self:
        return cls.from_post(view.post, view.author_name)


class TeamBoardPageOut(BaseModel):
    items: list[TeamBoardPostOut]
    replies: list[TeamBoardPostOut]
    total: int
    offset: int
    limit: int
    next_offset: int | None
    unread_count: int

    @classmethod
    def from_page(cls, page: TeamBoardPage) -> Self:
        return cls(
            items=[TeamBoardPostOut.from_view(item) for item in page.items],
            replies=[TeamBoardPostOut.from_view(item) for item in page.replies],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
            next_offset=page.next_offset,
            unread_count=page.unread_count,
        )
