"""Configuration read by keyword collectors, independent of request-scoped sessions."""

from typing import Protocol

from ase.domain.collection import CollectionPlan


class WatchlistPlanStore(Protocol):
    async def enabled_plans(self) -> list[CollectionPlan]: ...
