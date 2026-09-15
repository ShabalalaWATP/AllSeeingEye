"""Exact Research Brief revision loading for subscription creation and execution."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.research_brief_models import ResearchBriefRevisionRow
from ase.adapters.persistence.research_briefs import _decode
from ase.application.access import AccessContext
from ase.domain.errors import NotFound
from ase.domain.research_brief import ResearchBrief
from ase.domain.schedules import Schedule


async def load_brief_revision(
    session: AsyncSession,
    access: AccessContext,
    brief_id: UUID,
    revision: int,
    *,
    owner_id: UUID | None = None,
    team_id: UUID | None = None,
) -> ResearchBrief:
    """Load only an exact immutable revision in the subscription's current scope."""
    row = await session.get(ResearchBriefRevisionRow, (brief_id, revision), populate_existing=True)
    if row is None:
        raise NotFound("Research Brief revision not found.")
    if owner_id is None:
        access.require_read(row.owner_id, row.team_id)
    else:
        access.require_same_scope(owner_id, team_id, row.owner_id, row.team_id)
    return _decode(row)


async def load_schedule_brief(
    session: AsyncSession, access: AccessContext, schedule: Schedule
) -> ResearchBrief | None:
    if schedule.brief_id is None or schedule.brief_revision is None:
        return None
    return await load_brief_revision(
        session,
        access,
        schedule.brief_id,
        schedule.brief_revision,
        owner_id=schedule.created_by,
        team_id=schedule.team_id,
    )
