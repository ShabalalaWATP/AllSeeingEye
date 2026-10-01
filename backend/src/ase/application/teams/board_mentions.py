"""Resolve board @mentions against the team's current roster and keep them with the post.

Resolution uses only the authorised team roster: active members with a directory handle.
Global directory discovery and its opt-in are not consulted, and an unknown or outside
handle is indistinguishable from plain text. Changes are written in the caller's
transaction, so a failed or conflicting post write leaves no notice behind.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ase.application.bell.scope import BellSignals
from ase.application.ports.board_mentions import BoardMentionRepository
from ase.application.ports.teams import TeamRepository
from ase.domain.board_mentions import Mentioned, mentioned_handles
from ase.domain.errors import InvalidRequest
from ase.domain.team_board import TeamBoardPost


@dataclass(frozen=True, slots=True)
class BoardWrite:
    post: TeamBoardPost
    # Teammates this write newly notified; unchanged mentions are not repeated.
    notified: tuple[Mentioned, ...] = ()


@dataclass(frozen=True, slots=True)
class MentionChange:
    notified: tuple[Mentioned, ...]
    # Recipients whose bell changed, signalled after the commit.
    affected: frozenset[UUID]


class BoardMentions:
    def __init__(
        self, mentions: BoardMentionRepository, teams: TeamRepository, signals: BellSignals
    ) -> None:
        self._mentions = mentions
        self._teams = teams
        self._signals = signals

    @staticmethod
    def parse(text: str) -> tuple[str, ...]:
        """Validate before any write so the cap is enforced visibly on the text field."""
        try:
            return mentioned_handles(text)
        except ValueError as exc:
            raise InvalidRequest(str(exc), fields={"text": str(exc)}) from exc

    async def record(
        self, post: TeamBoardPost, handles: Sequence[str], now: datetime
    ) -> MentionChange:
        """Keep unchanged mentions as stored, drop removed ones and resolve only new ones."""
        existing = await self._mentions.for_post(post.id)
        removed = [handle for handle in existing if handle not in handles]
        kept = {existing[handle] for handle in handles if handle in existing}
        wanted = [handle for handle in handles if handle not in existing]
        added: dict[str, UUID] = {}
        notified: list[Mentioned] = []
        if wanted:
            roster = {
                member.username: member
                for member in await self._teams.list_members(post.team_id)
                if member.username is not None and member.is_active
            }
            for handle in wanted:
                member = roster.get(handle)
                if member is None or member.user_id == post.author_id or member.user_id in kept:
                    continue
                if member.user_id in added.values():
                    continue
                added[handle] = member.user_id
                notified.append(Mentioned(member.user_id, member.display_name))
        await self._mentions.remove(post.id, removed)
        if added:
            await self._mentions.add(post.id, post.team_id, added, now)
        affected = {existing[handle] for handle in removed} | set(added.values())
        notified.sort(key=lambda item: (item.display_name, str(item.user_id)))
        return MentionChange(tuple(notified), frozenset(affected))

    async def clear(self, post_id: UUID) -> frozenset[UUID]:
        return await self._mentions.clear(post_id)

    async def announce(self, recipients: Iterable[UUID]) -> None:
        await self._signals.users(recipients)
