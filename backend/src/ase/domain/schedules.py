"""Recurring research at a fixed UTC hour, including calendar-monthly runs."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportStatus
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchMode
from ase.domain.research_area import ResearchArea
from ase.domain.research_changes import ResearchChange
from ase.domain.research_records import ResearchReceipt
from ase.domain.research_scope import normalise_countries
from ase.domain.subscription_recurrence import LocalOccurrence, LocalRecurrence, WindowPolicy

CADENCES = ("daily", "weekdays", "weekly", "monthly", "quarterly", "semiannual", "annual")
MONTH_INTERVALS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}


class CoverageState(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ScheduleErrorCode(StrEnum):
    REPORT_FAILED = "report_failed"
    REVIEW_REQUIRED = "review_required"
    PARTIAL_COVERAGE = "partial_coverage"
    PRODUCTION_FAILED = "production_failed"
    SCHEDULE_BLOCKED = "schedule_blocked"


def coverage_state(
    receipt: ResearchReceipt | None, *, research_required: bool = False
) -> CoverageState:
    if receipt is None:
        return CoverageState.PARTIAL if research_required else CoverageState.NOT_APPLICABLE
    complete = {CollectionStatus.COMPLETED, CollectionStatus.EMPTY}
    return (
        CoverageState.COMPLETE
        if receipt.attempts and all(item.status in complete for item in receipt.attempts)
        else CoverageState.PARTIAL
    )


@dataclass(frozen=True, slots=True)
class ScheduleRunResult:
    report_id: UUID
    version_id: UUID
    outcome: ReportStatus
    coverage: CoverageState
    error_code: ScheduleErrorCode | None

    @classmethod
    def from_version(
        cls, version: ReportVersion, *, research_required: bool = False
    ) -> ScheduleRunResult:
        coverage = coverage_state(version.research, research_required=research_required)
        error_code = (
            ScheduleErrorCode.REPORT_FAILED
            if version.status is ReportStatus.FAILED
            else ScheduleErrorCode.REVIEW_REQUIRED
            if version.status is ReportStatus.NEEDS_REVIEW
            else ScheduleErrorCode.PARTIAL_COVERAGE
            if coverage is CoverageState.PARTIAL
            else None
        )
        return cls(version.report_id, version.id, version.status, coverage, error_code)

    @property
    def successful(self) -> bool:
        return self.outcome is ReportStatus.READY and self.coverage is not CoverageState.PARTIAL


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
    last_version_id: UUID | None = None
    last_outcome: ReportStatus | None = None
    last_coverage: CoverageState | None = None
    timezone: str = "UTC"
    local_hour: int | None = None
    local_minute: int = 0
    collection_policy: WindowPolicy = WindowPolicy.ROLLING_SNAPSHOT
    brief_id: UUID | None = None
    brief_revision: int | None = None
    archived_at: datetime | None = None

    def __post_init__(self) -> None:
        countries = normalise_countries(self.country_iso, self.country_isos)
        object.__setattr__(self, "country_isos", countries)
        object.__setattr__(self, "country_iso", countries[0] if len(countries) == 1 else None)
        if self.local_hour is None:
            object.__setattr__(self, "local_hour", self.hour_utc)
        _ = self.recurrence
        if not isinstance(self.collection_policy, WindowPolicy):
            raise ValueError("Choose a supported collection window policy.")
        if (self.brief_id is None) != (self.brief_revision is None) or (
            self.brief_revision is not None and self.brief_revision < 1
        ):
            raise ValueError("A linked Research Brief needs an exact positive revision.")
        if self.archived_at is not None and (self.enabled or self.archived_at.utcoffset() is None):
            raise ValueError("An archived subscription must be disabled and timestamped in UTC.")

    @property
    def recurrence(self) -> LocalRecurrence:
        if self.local_hour is None:  # pragma: no cover (normalised in __post_init__)
            raise ValueError("A local hour is required.")
        return LocalRecurrence(
            self.timezone,
            self.local_hour,
            self.local_minute,
            self.cadence,
            self.weekday,
            self.monthday,
            self.anchor_month,
        )

    @property
    def next_three(self) -> tuple[LocalOccurrence, ...]:
        return self.recurrence.next_three(self.next_run_at - timedelta(microseconds=1))


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
