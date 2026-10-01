"""Bounded JSON contracts for the plain-text team board."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.domain.board_mentions import Mentioned
from ase.domain.team_board import (
    MAX_REASON_LENGTH,
    BoardSubject,
    BoardSubjectKind,
    BoardSubjectView,
    ReportDiscussion,
    TeamBoardPage,
    TeamBoardPost,
    TeamBoardPostView,
)


class TeamBoardSubjectIn(BaseModel):
    """A same-team report version, saved area or drawing collection; checked server-side."""

    model_config = ConfigDict(extra="forbid")

    kind: BoardSubjectKind
    id: UUID
    version: int | None = Field(default=None, ge=1, le=100_000)

    @model_validator(mode="after")
    def _shape(self) -> Self:
        self.to_subject()  # Only a report version names a version number.
        return self

    def to_subject(self) -> BoardSubject:
        return BoardSubject(self.kind, self.id, self.version)


class TeamBoardSubjectOut(BaseModel):
    """Only an available subject carries its identifier and title."""

    kind: BoardSubjectKind
    id: UUID | None
    version: int | None
    available: bool
    title: str | None

    @classmethod
    def from_view(cls, view: BoardSubjectView) -> Self:
        available = view.available
        return cls(
            kind=view.subject.kind,
            id=view.subject.id if available else None,
            version=view.subject.version,
            available=available,
            title=view.title if available else None,
        )


class TeamBoardPostIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)
    parent_id: UUID | None = None
    subject: TeamBoardSubjectIn | None = None


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
    subject: TeamBoardSubjectOut | None

    @classmethod
    def from_post(
        cls, post: TeamBoardPost, author_name: str, subject: BoardSubjectView | None = None
    ) -> Self:
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
            subject=TeamBoardSubjectOut.from_view(subject) if subject else None,
        )

    @classmethod
    def from_view(cls, view: TeamBoardPostView) -> Self:
        return cls.from_post(view.post, view.author_name, view.subject)


class TeamBoardMentionedOut(BaseModel):
    user_id: UUID
    display_name: str


class TeamBoardWriteOut(TeamBoardPostOut):
    """A saved post plus the teammates this write newly notified (never outsiders)."""

    notified: list[TeamBoardMentionedOut]

    @classmethod
    def extend(cls, base: TeamBoardPostOut, notified: tuple[Mentioned, ...]) -> Self:
        return cls(
            **base.model_dump(),
            notified=[
                TeamBoardMentionedOut(user_id=item.user_id, display_name=item.display_name)
                for item in notified
            ],
        )


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


class ReportDiscussionOut(BaseModel):
    """Live board threads about any version of a team report; personal reports have none."""

    team_id: UUID | None
    count: int
    latest_post_id: UUID | None
    can_post: bool

    @classmethod
    def from_discussion(cls, discussion: ReportDiscussion) -> Self:
        return cls(
            team_id=discussion.team_id,
            count=discussion.count,
            latest_post_id=discussion.latest_post_id,
            can_post=discussion.can_post,
        )
