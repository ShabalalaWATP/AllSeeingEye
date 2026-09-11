"""Translate saved recurring options into the same request used by interactive research."""

from ase.application.reports.request import ReportRequest
from ase.domain.schedules import Schedule


def scheduled_report_request(schedule: Schedule) -> ReportRequest:
    return ReportRequest(
        template_id=schedule.template_id,
        country_iso=schedule.country_iso,
        country_isos=schedule.country_isos,
        window_hours=schedule.window_hours,
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
    )
