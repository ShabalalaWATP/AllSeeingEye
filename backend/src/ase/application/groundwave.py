"""Bounded explicit native calculations, isolated from the API event loop."""

import asyncio
from uuid import UUID

from ase.application.ports.groundwave import GroundwaveSolver
from ase.application.ports.services import RateLimiter
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.groundwave import GroundwaveInput, GroundwaveSample


class GroundwaveStudy:
    def __init__(
        self, solver: GroundwaveSolver, limiter: RateLimiter, *, timeout: float = 5
    ) -> None:
        self._solver, self._limiter, self._timeout = solver, limiter, timeout
        self._semaphore = asyncio.Semaphore(1)
        self._task: asyncio.Task[tuple[GroundwaveSample, ...]] | None = None

    async def _run(self, inputs: GroundwaveInput) -> tuple[GroundwaveSample, ...]:
        try:
            return await asyncio.to_thread(self._solver.calculate, inputs)
        finally:
            self._semaphore.release()

    async def calculate(
        self, actor_id: UUID, inputs: GroundwaveInput
    ) -> tuple[GroundwaveSample, ...]:
        retry = self._limiter.hit(f"groundwave:{actor_id}", 6, 60)
        if retry is not None:
            raise RateLimited(retry)
        if self._semaphore.locked():
            raise RateLimited(2)
        await self._semaphore.acquire()
        task = asyncio.create_task(self._run(inputs))
        self._task = task
        # Retain capacity until the native worker really finishes, even after HTTP timeout.
        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        try:
            return await asyncio.wait_for(asyncio.shield(task), self._timeout)
        except Exception:
            raise InvalidRequest(
                "The native groundwave model could not complete this study. "
                "No estimated range was substituted. Retry with different inputs."
            ) from None
