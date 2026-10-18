"""Run established expiry rules even when collection, delivery and accounts are idle."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from ase.adapters.persistence.dormant_retention import (
    BATCH,
    prune_alert_history,
    prune_push_receipts,
    prune_research_counters,
)
from ase.adapters.persistence.selected_index_expiry import expire_selected_metadata
from ase.adapters.persistence.users import SqlUserRepository
from ase.adapters.persistence.warning_consumption import prune_batch
from ase.application.worker_progress import run_cycle

if TYPE_CHECKING:
    from ase.container import Container

log = structlog.get_logger(__name__)
PHASE_TIMEOUT_SECONDS = 30


async def _cycle(name: str, operation: Callable[[], Awaitable[None]]) -> None:
    async def bounded() -> None:
        # TimeoutError must reach run_cycle, so it records a failed heartbeat;
        # external shutdown cancellation must still propagate unchanged.
        async with asyncio.timeout(PHASE_TIMEOUT_SECONDS):
            await operation()

    try:
        await run_cycle(f"retention_{name}", 60, bounded)
    except Exception:
        # Driver messages can contain SQL parameters or connection details.
        log.warning("dormant_retention.failed", category=name)


async def _repeat(name: str, operation: Callable[[], Awaitable[None]]) -> None:
    while True:
        await _cycle(name, operation)
        await asyncio.sleep(60)


@dataclass
class DormantRetention:
    container: Container
    selected_after: int | None = None
    selected_through: int | None = None
    consumed_after: UUID | None = None
    consumed_through: UUID | None = None

    async def selected(self) -> None:
        async with self.container.session_factory() as session:
            cursor, through, _ = await expire_selected_metadata(
                session,
                self.container.clock.now(),
                after=self.selected_after,
                through=self.selected_through,
                limit=BATCH,
            )
            await session.commit()
        self.selected_after = cursor
        self.selected_through = through

    async def consumed(self) -> None:
        async with self.container.session_factory() as session:
            await SqlUserRepository(session).lock_administration()
            cursor, through, _ = await prune_batch(
                session,
                self.container.clock.now(),
                after=self.consumed_after,
                through=self.consumed_through,
                limit=BATCH,
            )
            await session.commit()
        self.consumed_after = cursor
        self.consumed_through = through

    async def alerts(self) -> None:
        async with self.container.session_factory() as session:
            await prune_alert_history(session, self.container.clock.now())
            await session.commit()

    async def push(self) -> None:
        async with self.container.session_factory() as session:
            await prune_push_receipts(session, self.container.clock.now())
            await session.commit()

    async def research(self) -> None:
        async with self.container.session_factory() as session:
            await prune_research_counters(session, self.container.clock.now())
            await session.commit()

    async def ai(self) -> None:
        # Pruning preserves held reservations. Reconciliation is a separate policy
        # and must not settle an uncertain provider call merely because it is idle.
        await self.container.ai_usage_accounting.prune(limit=BATCH)

    async def private_inputs(self) -> None:
        # The store is already capped at 24 slots and is owned by this event loop.
        self.container.research_inputs.expire()

    def phases(self) -> tuple[tuple[str, Callable[[], Awaitable[None]]], ...]:
        return (
            ("private_inputs", self.private_inputs),
            ("selected", self.selected),
            ("consumed", self.consumed),
            ("alerts", self.alerts),
            ("push", self.push),
            ("research", self.research),
            ("ai", self.ai),
        )

    async def cycle(self) -> None:
        """One serial maintenance pass, useful for controlled checks."""
        for name, operation in self.phases():
            await _cycle(name, operation)


async def run_dormant_retention(container: Container) -> None:
    maintenance = DormantRetention(container)
    # Each category owns its cadence. Stalled SQL must not delay memory expiry or
    # unrelated heartbeats. TaskGroup joins every child before database disposal.
    async with asyncio.TaskGroup() as tasks:
        for name, operation in maintenance.phases():
            tasks.create_task(_repeat(name, operation), name=f"retention_{name}")
