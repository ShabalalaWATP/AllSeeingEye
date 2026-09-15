"""Global-only model resolution and short publication guards for shared screening."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.application.conflict_screening.model import LlmConflictScreener
from ase.application.conflict_screening.queue import ConflictScreeningQueue, ScreeningGeneration
from ase.application.model_routing import ModelRouting
from ase.domain.errors import NoModelAvailable
from ase.domain.events import content_hash
from ase.domain.llm import LlmRole, LlmUsage

if TYPE_CHECKING:
    from ase.container import Container


class GlobalScreeningRuntime:
    def __init__(self, container: Container) -> None:
        self.container = container

    async def _resolve(self, session: AsyncSession) -> ScreeningGeneration | None:
        repos = self.container.repositories(session)
        await repos.users.lock_administration()
        try:
            routing = await ModelRouting(repos.llm_profiles, repos.llm_bindings).snapshot()
        except NoModelAvailable:
            return None
        profile = routing.required(LlmRole.ASSESSMENT)
        binding = await repos.llm_bindings.get(None)
        key = content_hash(
            str(binding.revision) if binding else "legacy", str(profile.id), profile.config_hash
        )
        return ScreeningGeneration(key, profile)

    async def resolve(self) -> ScreeningGeneration | None:
        if not self.container.cipher.available:
            return None
        async with self.container.session_factory() as session:
            return await self._resolve(session)

    @asynccontextmanager
    async def release(self, generation: ScreeningGeneration) -> AsyncIterator[bool]:
        # Same order as source administration. Never hold either lock across a model call.
        async with (
            self.container.source_admission.guard(),
            self.container.session_factory() as session,
        ):
            current = await self._resolve(session)
            yield current is not None and current.key == generation.key


def build_conflict_screening(container: Container) -> ConflictScreeningQueue:
    async def save_usage(usage: LlmUsage) -> None:
        async with container.session_factory() as session:
            await container.repositories(session).llm_usage.add(usage)
            await session.commit()

    return ConflictScreeningQueue(
        container.store,
        container.bus,
        LlmConflictScreener(
            container.system_llm_gateway(), container.cipher, container.clock, save_usage
        ),
        GlobalScreeningRuntime(container),
        container.source_admission,
        container.clock,
        enabled=container.settings.conflict_screening_enabled,
        calls_per_hour=container.settings.conflict_screening_calls_per_hour,
    )
