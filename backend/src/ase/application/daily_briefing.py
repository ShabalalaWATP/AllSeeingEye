"""Once-daily personal briefings through the authorised, durable report pipeline."""

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.report_jobs import ReportJobRepository
from ase.application.report_jobs.service import ReportJobService, SessionCheck
from ase.application.reports.request import ReportRequest
from ase.domain.daily_briefing import REFRESH_INTERVAL, briefing_key
from ase.domain.events import Category
from ase.domain.research import ResearchMode
from ase.domain.users import User

__all__ = ["DailyBriefingService", "briefing_key", "briefing_request"]

COVERAGE_NOTE = (
    "This briefing covers evidence available from enabled sources in the previous 24 hours. "
    "Coverage varies by region and topic; missing reporting does not mean nothing happened."
)


def briefing_request() -> ReportRequest:
    return ReportRequest(
        template_id="ask",
        question=(
            "Daily global situation briefing: what significant developments were reported "
            "in armed conflicts, natural disasters and associated humanitarian crises in "
            "the past 24 hours? Provide a concise overall situation summary, the main "
            "dated news developments by region and topic, and what to watch next. "
            "Distinguish armed conflict from accidents and peaceful protests, and verified "
            "events from claims. Use in-text citations and identify missing or stale "
            "coverage; do not infer that a region is calm because no sources were collected."
        ),
        categories=(Category.CONFLICT, Category.DISASTER, Category.HUMANITARIAN, Category.NEWS),
        window_hours=24,
        research_mode=ResearchMode.QUICK,
        report_style="briefing",
    )


@dataclass(frozen=True, slots=True)
class DailyBriefing:
    job: dict[str, Any]
    next_refresh_at: datetime
    coverage_note: str = COVERAGE_NOTE


class DailyBriefingService:
    """Admission requires a POST; GET requests never start provider work.

    Three bounded date lookups cover preparation crossing UTC midnight while
    preserving a rolling 24-hour minimum between persisted admissions.
    The underlying admission key and shared account guard serialise competing POSTs.
    Failed/paused jobs are returned unchanged, avoiding invisible paid retry loops.
    """

    def __init__(
        self,
        jobs: ReportJobService,
        repo: ReportJobRepository,
        uow: UnitOfWork,
        clock: Clock,
        admission_guard: AbstractAsyncContextManager[None],
    ) -> None:
        self._jobs, self._repo, self._uow, self._clock = jobs, repo, uow, clock
        self._admission_guard = admission_guard

    async def ensure(
        self,
        actor: User,
        context: RequestContext,
        *,
        check_session: SessionCheck,
    ) -> DailyBriefing:
        await check_session()
        async with self._admission_guard:
            return await self._ensure(actor, context, check_session=check_session)

    async def _ensure(
        self,
        actor: User,
        context: RequestContext,
        *,
        check_session: SessionCheck,
    ) -> DailyBriefing:
        now = self._clock.now()
        try:
            for instant in (now, now - REFRESH_INTERVAL, now - 2 * REFRESH_INTERVAL):
                existing = await self._repo.get_by_request(
                    actor.id, briefing_key(actor.id, instant)
                )
                if existing is not None and now < existing.created_at + REFRESH_INTERVAL:
                    break
            else:
                existing = None
        finally:
            await self._uow.rollback()
        if existing is not None:
            # Read rechecks current ownership, session and source controls before release.
            view = await self._jobs.read(actor, existing.id, check_session=check_session)
        else:
            view = await self._jobs.create(
                actor,
                briefing_key(actor.id, now),
                briefing_request(),
                context,
                check_session=check_session,
            )
        created_at = view["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return DailyBriefing(view, created_at + REFRESH_INTERVAL)
