"""Pure report display metadata and period helpers."""

from datetime import timedelta
from typing import Any

from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import Template
from ase.domain.collection import CollectionPlan
from ase.domain.trackers import HAZARD_TITLES, Conflict, Hazard


def report_window(request: ReportRequest, template: Template) -> timedelta:
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
        "country": request.country_iso,
        "categories": [category.value for category in request.categories],
        "question": request.question,
        "window_hours": int(report_window(request, template).total_seconds() // 3600),
        "devils_advocacy": request.devils_advocacy,
        "hazard": request.hazard,
        "conflict": request.conflict_id,
        "plan": str(request.plan_id) if request.plan_id else None,
    }
