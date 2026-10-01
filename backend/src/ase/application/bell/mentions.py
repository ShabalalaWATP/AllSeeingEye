"""Board mentions in the bell: each recipient's own unread notices, re-checked on every read."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from ase.application.access import AccessContext, AccessPolicy
from ase.application.bell.scope import BellSignals
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.board_mentions import BoardMentionRepository
from ase.domain.bell import BELL_SHOWN, BellKind, BellPreferences
from ase.domain.board_mentions import MentionNotice, MentionSection
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.team_board import UNREAD_COUNT_CAP
from ase.domain.users import User

MAX_READ_BATCH = 20


class BellMentions:
    def __init__(
        self,
        mentions: BoardMentionRepository,
        access: AccessPolicy,
        clock: Clock,
        uow: UnitOfWork,
        signals: BellSignals,
    ) -> None:
        self._mentions = mentions
        self._access = access
        self._clock = clock
        self._uow = uow
        self._signals = signals

    async def section(self, access: AccessContext, preferences: BellPreferences) -> MentionSection:
        if not preferences.shows(BellKind.MENTIONS):
            return MentionSection((), 0, muted=True)
        items, unread = await self._mentions.notices(access.actor.id, BELL_SHOWN, UNREAD_COUNT_CAP)
        return MentionSection(tuple(items), unread, muted=False)

    async def open(self, actor: User, post_id: UUID) -> MentionNotice:
        """Where a mention leads, only while the post is still readable; marks it read."""
        access = await self._access.context(actor)
        notice = await self._mentions.notice(access.actor.id, post_id)
        if notice is None:
            raise NotFound("This mention is no longer available.")
        if notice.read_at is None:
            await self._mentions.mark_read(access.actor.id, (post_id,), self._clock.now())
            await self._uow.commit()
            await self._signals.users((access.actor.id,))
        return notice

    async def mark_read(self, actor: User, post_ids: Sequence[UUID]) -> int:
        """Mark the caller's own notices read; returns their remaining unread count."""
        unique = tuple(dict.fromkeys(post_ids))
        if not 1 <= len(unique) <= MAX_READ_BATCH:
            raise InvalidRequest(f"Mark 1 to {MAX_READ_BATCH} mentions at a time.")
        access = await self._access.context(actor)
        await self._mentions.mark_read(access.actor.id, unique, self._clock.now())
        await self._uow.commit()
        await self._signals.users((access.actor.id,))
        _, unread = await self._mentions.notices(access.actor.id, 0, UNREAD_COUNT_CAP)
        return unread
