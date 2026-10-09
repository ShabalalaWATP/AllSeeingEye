"""Convert scheduled-product rows without performing persistence or authorisation."""

from uuid import UUID

from ase.adapters.persistence.models import ScheduleRow
from ase.domain.events import Category
from ase.domain.regions import Region
from ase.domain.reports import ReportStatus
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_area import area_from_dict, area_to_dict
from ase.domain.research_changes import change_from_dict, change_to_dict
from ase.domain.schedules import CoverageState, Schedule
from ase.domain.subscription_recurrence import WindowPolicy


def schedule_from_row(row: ScheduleRow) -> Schedule:
    options = row.research_options or {}
    return Schedule(
        id=row.id,
        name=row.name,
        template_id=row.template_id,
        country_iso=row.country_iso,
        plan_id=row.plan_id,
        hour_utc=row.hour_utc,
        timezone=row.timezone,
        local_hour=row.local_hour,
        local_minute=row.local_minute,
        collection_policy=WindowPolicy(row.collection_policy),
        brief_id=row.brief_id,
        brief_revision=row.brief_revision,
        cadence=row.cadence,
        weekday=row.weekday,
        window_hours=row.window_hours,
        enabled=row.enabled,
        archived_at=row.archived_at,
        created_by=row.created_by,
        created_at=row.created_at,
        next_run_at=row.next_run_at,
        last_run_at=row.last_run_at,
        last_report_id=row.last_report_id,
        last_error=row.last_error,
        team_id=row.team_id,
        notify_on_change=row.notify_on_change,
        last_change=change_from_dict(row.last_change),
        question=row.question,
        research_mode=ResearchMode(options["mode"]) if options.get("mode") else None,
        research_languages=tuple(options.get("languages") or ["en"]),
        research_focus=ResearchFocus(options.get("focus", "general")),
        research_subject=options.get("subject"),
        country_isos=tuple(options.get("country_isos", ())),
        monthday=options.get("monthday", 1),
        research_web_search=options.get("web_search", False),
        research_source_ids=tuple(options["source_ids"])
        if options.get("source_ids") is not None
        else None,
        anchor_month=options.get("anchor_month", 1),
        conflict_id=options.get("conflict_id"),
        hazard=options.get("hazard"),
        categories=tuple(Category(value) for value in options.get("categories", ())),
        regions=tuple(Region(value) for value in options.get("regions", ())),
        research_area=area_from_dict(options.get("research_area")),
        disclose_area_to_provider=options.get("disclose_area_to_provider", False),
        avoid_repetition=options.get("avoid_repetition", True),
        seen_content_signatures=tuple(options.get("seen_content_signatures", ()))[:500],
        baseline_report_id=UUID(options["baseline_report_id"])
        if options.get("baseline_report_id")
        else None,
        last_version_id=UUID(options["last_version_id"])
        if options.get("last_version_id")
        else None,
        last_outcome=ReportStatus(options["last_outcome"]) if options.get("last_outcome") else None,
        last_coverage=CoverageState(options["last_coverage"])
        if options.get("last_coverage")
        else CoverageState.UNKNOWN
        if "last_coverage" not in options and (row.last_run_at or row.last_report_id)
        else None,
    )


def fill_schedule_row(row: ScheduleRow, schedule: Schedule) -> None:
    row.name = schedule.name
    row.template_id = schedule.template_id
    row.country_iso = schedule.country_iso
    row.plan_id = schedule.plan_id
    row.hour_utc = schedule.hour_utc
    row.timezone = schedule.timezone
    row.local_hour = schedule.local_hour if schedule.local_hour is not None else schedule.hour_utc
    row.local_minute = schedule.local_minute
    row.collection_policy = schedule.collection_policy.value
    row.brief_id = schedule.brief_id
    row.brief_revision = schedule.brief_revision
    row.cadence = schedule.cadence
    row.weekday = schedule.weekday
    row.window_hours = schedule.window_hours
    row.enabled = schedule.enabled
    row.archived_at = schedule.archived_at
    row.created_by = schedule.created_by
    row.created_at = schedule.created_at
    row.next_run_at = schedule.next_run_at
    row.last_run_at = schedule.last_run_at
    row.last_report_id = schedule.last_report_id
    row.last_error = schedule.last_error
    row.team_id = schedule.team_id
    row.notify_on_change = schedule.notify_on_change
    row.last_change = change_to_dict(schedule.last_change)
    row.question = schedule.question
    row.research_options = {
        "mode": schedule.research_mode.value if schedule.research_mode else None,
        "languages": list(schedule.research_languages),
        "focus": schedule.research_focus.value,
        "subject": schedule.research_subject,
        "country_isos": list(schedule.country_isos),
        "monthday": schedule.monthday,
        "anchor_month": schedule.anchor_month,
        "conflict_id": schedule.conflict_id,
        "hazard": schedule.hazard,
        "categories": [category.value for category in schedule.categories],
        "regions": [region.value for region in schedule.regions],
        "research_area": area_to_dict(schedule.research_area),
        "disclose_area_to_provider": schedule.disclose_area_to_provider,
        "avoid_repetition": schedule.avoid_repetition,
        "seen_content_signatures": list(schedule.seen_content_signatures),
        "baseline_report_id": str(schedule.baseline_report_id)
        if schedule.baseline_report_id
        else None,
        "last_version_id": str(schedule.last_version_id) if schedule.last_version_id else None,
        "last_outcome": schedule.last_outcome.value if schedule.last_outcome else None,
        "last_coverage": schedule.last_coverage.value if schedule.last_coverage else None,
        "web_search": schedule.research_web_search,
        "source_ids": list(schedule.research_source_ids)
        if schedule.research_source_ids is not None
        else None,
    }
