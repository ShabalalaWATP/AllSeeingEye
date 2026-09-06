"""Ports for social configuration and the small hourly aggregate store."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol

from ase.domain.social import SocialBaseline, WatchedTerm
from ase.domain.users import User


class SocialTermsSource(Protocol):
    async def configured(self) -> tuple[WatchedTerm, ...]: ...
    async def visible_to(self, actor: User) -> tuple[WatchedTerm, ...]: ...


class SocialActivityStore(Protocol):
    async def record(self, hour: datetime, counts: Mapping[str, int]) -> None:
        """Write one bounded hour and prune stale history and removed vocabulary."""
        ...

    async def baselines(
        self, since: datetime, before: datetime, keys: Sequence[str]
    ) -> Mapping[str, SocialBaseline]: ...
