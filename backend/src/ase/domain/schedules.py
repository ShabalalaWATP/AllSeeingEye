"""Scheduled products: a standing order for a report at a fixed UTC hour, daily or weekly."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_changes import ResearchChange

CADENCES = ("daily", "weekdays", "weekly")


@dataclass(frozen=True, slots=True)
class Schedule:
    id: UUID
    name: str
    template_id: str
    country_iso: str | None
    plan_id: UUID | None
    hour_utc: int
    cadence: str
    weekday: int
    window_hours: int | None
    enabled: bool
    created_by: UUID
    created_at: datetime
    next_run_at: datetime
    last_run_at: datetime | None = None
    last_report_id: UUID | None = None
    last_error: str | None = None
    team_id: UUID | None = None
    notify_on_change: bool = False
    last_change: ResearchChange | None = None
    question: str | None = None
    research_mode: ResearchMode | None = None
    research_languages: tuple[str, ...] = ("en",)
    research_focus: ResearchFocus = ResearchFocus.GENERAL
    research_subject: str | None = None


def next_run_after(now: datetime, hour_utc: int, cadence: str, weekday: int = 0) -> datetime:
    """The first moment strictly after `now` at hour_utc:00 UTC that the cadence allows."""
    candidate = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    for _ in range(8):
        day = candidate.weekday()
        if cadence == "daily":
            return candidate
        if cadence == "weekdays" and day < 5:
            return candidate
        if cadence == "weekly" and day == weekday:
            return candidate
        candidate += timedelta(days=1)
    return candidate  # pragma: no cover (every cadence answers within a week)
