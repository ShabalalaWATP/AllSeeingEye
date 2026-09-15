"""Compose guarded original acquisition only under a leased report job."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ase.adapters.research.original_http import GuardedOriginalHttp
from ase.application.access import AccessContext
from ase.application.reports.original_followthrough import OriginalFollowThrough
from ase.application.research.original_policy import OriginalSourcePolicy
from ase.container.report_original_staging import CheckedOriginalStaging

if TYPE_CHECKING:
    from ase.container import Container
    from ase.container.report_job_checkpoints import ReportJobCheckpoints
    from ase.domain.report_jobs import ReportJob


def make_original_followthrough(
    container: Container, stored: ReportJob, checkpoints: ReportJobCheckpoints
) -> OriginalFollowThrough:
    """No policy is bundled by default; an operator must supply reviewed source entries."""
    policies: dict[str, OriginalSourcePolicy] = getattr(container, "original_source_policies", {})

    async def current_access() -> AccessContext:
        async with container.session_factory() as session:
            access = await container.access_policy(session).background(
                stored.owner_id, stored.team_id
            )
            await session.rollback()
            return access

    async def admit_hop(source_id: str, url: str) -> bool:
        async with container.source_admission.guard():
            current = getattr(container, "original_source_policies", {}).get(source_id)
            if (
                current is None
                or not current.permits(url, container.clock.now())
                or not await container.source_admission.enabled(source_id)
            ):
                return False
            for name, limit in (
                (f"original-source:{source_id}", 6),
                ("original-source:global", 24),
            ):
                if container.limiter.hit(name, limit, 3600) is not None:
                    return False
            return True

    transport = GuardedOriginalHttp(container.settings.feeds_user_agent, container.clock, admit_hop)
    return OriginalFollowThrough(
        job_id=stored.id,
        specs={spec.id: spec for spec in container.research_sources},
        policies=policies,
        admission=container.source_admission,
        current_access=current_access,
        parser=container.research_importer,
        clock=container.clock,
        fetch=transport.fetch,
        staging=CheckedOriginalStaging(container, checkpoints),
        checkpoints=checkpoints,
    )
