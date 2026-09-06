"""Optional local stage notification, never a percentage or a new outbound request."""

from collections.abc import Awaitable, Callable

from ase.domain.research_runs import ResearchStage

Progress = Callable[[ResearchStage], Awaitable[None]]


async def reached(progress: Progress | None, stage: ResearchStage) -> None:
    if progress is not None:
        await progress(stage)
