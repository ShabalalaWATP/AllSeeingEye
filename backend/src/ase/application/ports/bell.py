"""Persistence boundary for the bell's alert reads and each account's bell preferences."""

from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.access import Visibility
from ase.domain.bell import BellKind, BellPreferences
from ase.domain.warning import Alert


class BellAlertQueries(Protocol):
    async def unacknowledged(
        self,
        visibility: Visibility,
        since: datetime,
        muted_rules: Collection[UUID],
        limit: int,
    ) -> tuple[list[Alert], int]:
        """Newest unacknowledged alerts and their total, filtered in SQL before the limit."""
        ...


class BellPreferenceRepository(Protocol):
    async def get(self, user_id: UUID, visibility: Visibility) -> BellPreferences:
        """The account's choices; muted rules are listed only while ``visibility`` reads them."""
        ...

    async def muted_rule_ids(self, user_id: UUID) -> frozenset[UUID]: ...

    async def set_kinds(self, user_id: UUID, kinds: frozenset[BellKind], now: datetime) -> None: ...

    async def count_rule_mutes(self, user_id: UUID) -> int: ...

    async def mute_rule(self, user_id: UUID, indicator_id: UUID, now: datetime) -> None:
        """Insert the mute unless it already exists."""
        ...

    async def unmute_rule(self, user_id: UUID, indicator_id: UUID) -> None: ...
