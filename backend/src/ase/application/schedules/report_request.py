"""Translate saved recurring options into the same request used by interactive research."""

from ase.application.reports.request import ReportRequest
from ase.domain.schedules import Schedule

LOOKBACK_DAYS = {
    "daily": 1,
    "weekdays": 3,
    "weekly": 7,
    "monthly": 31,
    "quarterly": 92,
    "semiannual": 184,
    "annual": 366,
}


def scheduled_report_request(schedule: Schedule) -> ReportRequest:
    return ReportRequest(
        template_id=schedule.template_id,
        country_iso=schedule.country_iso,
        country_isos=schedule.country_isos,
        window_hours=schedule.window_hours
        if schedule.window_hours is not None
        else LOOKBACK_DAYS[schedule.cadence] * 24,
        plan_id=schedule.plan_id,
        team_id=schedule.team_id,
        automation=True,
        question=schedule.question,
        research_mode=schedule.research_mode,
        research_languages=schedule.research_languages,
        research_focus=schedule.research_focus,
        research_subject=schedule.research_subject,
        research_web_search=schedule.research_web_search,
        research_source_ids=schedule.research_source_ids,
        conflict_id=schedule.conflict_id,
        hazard=schedule.hazard,
        research_area=schedule.research_area,
        disclose_area_to_provider=schedule.disclose_area_to_provider,
        subscription_previous_report_id=(schedule.baseline_report_id or schedule.last_report_id)
        if schedule.avoid_repetition
        else None,
        subscription_seen_signatures=schedule.seen_content_signatures
        if schedule.avoid_repetition
        else (),
    )
