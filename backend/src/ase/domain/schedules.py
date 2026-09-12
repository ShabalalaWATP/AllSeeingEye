"""Recurring research at a fixed UTC hour, including calendar-monthly runs."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_area import ResearchArea
from ase.domain.research_changes import ResearchChange
from ase.domain.research_scope import normalise_countries

CADENCES = ("daily", "weekdays", "weekly", "monthly", "quarterly", "semiannual", "annual")
MONTH_INTERVALS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}


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
    country_isos: tuple[str, ...] = ()
    monthday: int = 1
    research_web_search: bool = False
    research_source_ids: tuple[str, ...] | None = None
    anchor_month: int = 1
    conflict_id: str | None = None
    hazard: str | None = None
    research_area: ResearchArea | None = None
    disclose_area_to_provider: bool = False
    avoid_repetition: bool = True
    seen_content_signatures: tuple[str, ...] = ()
    baseline_report_id: UUID | None = None

    def __post_init__(self) -> None:
        countries = normalise_countries(self.country_iso, self.country_isos)
        object.__setattr__(self, "country_isos", countries)
        object.__setattr__(self, "country_iso", countries[0] if len(countries) == 1 else None)


def next_run_after(
    now: datetime,
    hour_utc: int,
    cadence: str,
    weekday: int = 0,
    monthday: int = 1,
    anchor_month: int = 1,
) -> datetime:
    """The first moment strictly after `now` at hour_utc:00 UTC that the cadence allows."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("The schedule clock must be timezone-aware")
    if cadence not in CADENCES or not 0 <= hour_utc <= 23:
        raise ValueError("Invalid schedule cadence or UTC hour")
    if not 0 <= weekday <= 6 or not 1 <= monthday <= 31 or not 1 <= anchor_month <= 12:
        raise ValueError("Invalid schedule weekday or day of month")
    now = now.astimezone(UTC)
    if cadence in MONTH_INTERVALS:
        # Keep the requested day. A short February must not turn future runs into the 28th.
        year, month = now.year, now.month
        for _ in range(13):
            candidate = datetime(
                year, month, min(monthday, monthrange(year, month)[1]), hour_utc, tzinfo=UTC
            )
            if candidate > now and (month - anchor_month) % MONTH_INTERVALS[cadence] == 0:
                return candidate
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        raise ValueError("Unable to resolve calendar recurrence")  # pragma: no cover
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
