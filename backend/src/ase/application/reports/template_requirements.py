"""Shared prerequisites for manual products and automated alert products."""

from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import Template
from ase.domain.collection import AreaOfInterest, CollectionPlan
from ase.domain.errors import InvalidRequest


def require_template_inputs(
    template: Template,
    request: ReportRequest,
    *,
    conflict_available: bool = False,
    hazard_available: bool = False,
) -> None:
    if template.needs_country and len(request.country_isos) != 1:
        message = "This template needs exactly one country."
        raise InvalidRequest(message, fields={"country": message})
    if template.needs_question and not (request.question or "").strip() and not request.plan_id:
        message = "This template needs a question."
        raise InvalidRequest(message, fields={"question": message})
    if template.needs_conflict and not conflict_available:
        message = "This template needs a conflict from the tracker list."
        raise InvalidRequest(message, fields={"conflict": message})
    if template.needs_hazard and not hazard_available:
        message = "This template needs a hazard from the disaster tracker."
        raise InvalidRequest(message, fields={"hazard": message})


def require_report_plan(plan: CollectionPlan | None, aoi: AreaOfInterest | None) -> None:
    if plan is None:
        return
    if not plan.pirs:
        raise InvalidRequest("The linked collection plan needs a question before use.")
    if plan.aoi_id is not None and aoi is None:
        raise InvalidRequest("The linked area is unavailable; repair the plan before use.")
    if aoi is not None and aoi.research_area is not None:
        raise InvalidRequest(
            "Use this exact area in standalone area research or an area subscription; "
            "collection-plan report templates cannot honour its polygon."
        )
