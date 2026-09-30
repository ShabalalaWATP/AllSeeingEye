"""Lifespan-scoped observation of real cycles, including healthy idle cycles.

The composition root binds the port while creating workers. Each worker task
inherits that binding, so unrelated applications and request tasks cannot stamp
its registry. Completion is recorded after awaited work, never by a timer.
"""

from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from ase.application.ports.worker_health import WorkerHeartbeats

worker_heartbeats: ContextVar[WorkerHeartbeats | None] = ContextVar(
    "worker_heartbeats", default=None
)


def register_worker(name: str, interval: float) -> None:
    if registry := worker_heartbeats.get():
        registry.register(name, interval)


async def run_cycle[T](name: str, interval: float, operation: Callable[[], Awaitable[T]]) -> T:
    registry = worker_heartbeats.get()
    if registry is not None:
        registry.register(name, interval)
    try:
        result = await operation()
    except Exception:
        if registry is not None:
            registry.completed(name, interval, "cycle_failed")
        raise
    else:
        if registry is not None:
            registry.completed(name, interval)
        return result
