"""Recheck source and session authority after a bounded board projection completes."""

from collections.abc import Awaitable, Callable

from ase.api.deps import ContainerDep
from ase.api.session_fence import FenceDep
from ase.domain.errors import RateLimited


async def read_board_response[T](
    container: ContainerDep, fence: FenceDep, work: Callable[[], Awaitable[T]]
) -> T:
    # Admission belongs to the store. Only the short final fence takes the
    # source guard, so requests cannot queue outside bounded read admission.
    generation = container.source_admission.generation
    enabled = await container.source_admission.enabled_many(tuple(container.source_profiles))
    result = await work()
    async with container.source_admission.guard():
        if container.source_admission.generation != generation:
            raise RateLimited(1)
        current = await container.source_admission.enabled_many(tuple(enabled))
        if any(value and not current.get(key, False) for key, value in enabled.items()):
            raise RateLimited(1)
        await fence.confirm()
        return result
