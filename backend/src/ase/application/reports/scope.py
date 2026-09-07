"""Pure report display metadata and period helpers."""

from dataclasses import asdict
from datetime import UTC, timedelta
from typing import Any

from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import Template
from ase.domain.collection import CollectionPlan
from ase.domain.map_research_origin import origin_to_dict
from ase.domain.trackers import HAZARD_TITLES, Conflict, Hazard


def report_window(request: ReportRequest, template: Template) -> timedelta:
    if request.research_since is not None and request.research_until is not None:
        return request.research_until - request.research_since
    return timedelta(hours=request.window_hours or template.strategy.window_hours)


def report_title(
    template: Template,
    request: ReportRequest,
    country: Any,
    conflict: Conflict | None,
    hazard: Hazard | None,
    plan: CollectionPlan | None = None,
) -> str:
    if plan is not None:
        return f"{template.title}: {plan.name}"
    if conflict is not None:
        return f"{template.title}: {conflict.name}"
    place = country.name if country else request.country_iso
    if hazard is not None:
        where = f" in {place}" if place else ""
        return f"{template.title}: {HAZARD_TITLES[hazard].lower()}{where}"
    if request.question:
        return f"{template.title}: {request.question.strip()[:120]}"
    if place:
        return f"{template.title}: {place}"
    return f"{template.title}: global"


def conflict_background(conflict: Conflict | None) -> str | None:
    if conflict is None:
        return None
    sides = ", ".join(conflict.belligerents) or "not listed"
    return f"{conflict.name} ({conflict.status}). {conflict.summary} Belligerents: {sides}."


def report_scope(request: ReportRequest, template: Template) -> dict[str, Any]:
    return {
        **(
            {"research_time_basis": request.research_time_basis.value}
            if request.research_time_basis is not None
            else {}
        ),
        **(
            {
                "research_since": request.research_since.astimezone(UTC).isoformat(),
                "research_until": request.research_until.astimezone(UTC).isoformat(),
            }
            if request.research_since is not None and request.research_until is not None
            else {}
        ),
        "report_language": request.report_language,
        "report_style": request.report_style,
        "country": request.country_iso,
        "categories": [category.value for category in request.categories],
        "question": request.question,
        "window_hours": int(report_window(request, template).total_seconds() // 3600),
        "devils_advocacy": request.devils_advocacy,
        "hazard": request.hazard,
        "conflict": request.conflict_id,
        "plan": str(request.plan_id) if request.plan_id else None,
        **(
            {
                "map_origin": origin_to_dict(request.map_origin),
                "disclose_area_to_provider": request.disclose_area_to_provider,
            }
            if request.map_origin
            else {}
        ),
        **(
            {
                **(
                    {
                        "research_candidate_hypotheses": [
                            {key: value for key, value in asdict(row).items() if key != "origin"}
                            for row in request.research_candidate_hypotheses
                        ]
                    }
                    if request.research_candidate_hypotheses
                    else {}
                ),
                **(
                    {
                        "research_planned_tasks": [
                            {key: value for key, value in asdict(row).items() if key != "origin"}
                            for row in request.research_planned_tasks
                        ]
                    }
                    if request.research_planned_tasks
                    else {}
                ),
                "research_mode": request.research_mode.value,
                "research_languages": list(request.research_languages),
                "research_source_ids": list(request.research_source_ids)
                if request.research_source_ids is not None
                else None,
                "research_query_variants": [asdict(row) for row in request.research_query_variants],
                "research_terms": list(request.research_terms)
                if request.research_terms is not None
                else None,
                "research_focus": request.research_focus.value,
                "research_subject": request.research_subject,
            }
            if request.research_mode
            else {}
        ),
    }
