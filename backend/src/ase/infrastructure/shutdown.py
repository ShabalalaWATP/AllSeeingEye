"""Dependency-ordered cleanup has a shared cooperative budget and safe phase logs."""

import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter

import structlog

log = structlog.get_logger(__name__)
SHUTDOWN_BUDGET_SECONDS = 18.0


class ShutdownPhases:
    def __init__(self, budget: float = SHUTDOWN_BUDGET_SECONDS) -> None:
        self.budget = budget
        self.started: float | None = None
        self.failed = False

    async def run(self, phase: str, callback: Callable[[], Awaitable[None]]) -> None:
        start = perf_counter()
        if self.started is None:
            self.started = start
        # Leave room for the final atomic snapshot and client disposal. Every
        # callback is attempted even if an earlier callback exhausted its allowance.
        reserved = 0 if phase == "dispose" else (1 if phase == "live_snapshot" else 4)
        remaining = max(0.01, self.budget - (start - self.started) - reserved)
        outcome = "completed"
        try:
            async with asyncio.timeout(remaining):
                await callback()
        except TimeoutError:
            outcome, self.failed = "timed_out", True
            raise
        except BaseException:
            outcome, self.failed = "failed", True
            raise
        finally:
            log.info(
                "shutdown.phase",
                phase=phase,
                duration_ms=round((perf_counter() - start) * 1000, 3),
                outcome=outcome,
            )

    def complete(self) -> None:
        duration = perf_counter() - self.started if self.started is not None else 0
        log.info(
            "shutdown.complete",
            duration_ms=round(duration * 1000, 3),
            outcome="failed" if self.failed else "completed",
        )
