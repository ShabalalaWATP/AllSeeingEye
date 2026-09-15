"""Subscription scope follows the same bounded request rules as ordinary research."""

from typing import TYPE_CHECKING

from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import Template
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchFocus
from ase.domain.trackers import Hazard

if TYPE_CHECKING:
    from ase.application.schedules.definition import ScheduleInput


def validate_subscription_scope(data: "ScheduleInput", template: Template) -> None:
    if data.research_area is not None and data.enabled and not data.disclose_area_to_provider:
        raise InvalidRequest(
            "Confirm disclosure of this area to providers before enabling updates."
        )
    if data.conflict_id and data.hazard:
        raise InvalidRequest("Choose a conflict or a natural hazard, not both.")
    if (data.conflict_id or data.hazard) and data.research_focus != ResearchFocus.GENERAL:
        raise InvalidRequest("Conflict and hazard subscriptions require general research.")
    if template.needs_conflict and not data.conflict_id:
        raise InvalidRequest("Choose a conflict from the tracker list.")
    if data.conflict_id is not None and (
        not data.conflict_id.strip() or len(data.conflict_id) > 120
    ):
        raise InvalidRequest("Choose a valid conflict identifier.")
    if template.needs_hazard and not data.hazard:
        raise InvalidRequest("Choose a natural hazard.")
    if data.hazard is not None:
        try:
            Hazard(data.hazard)
        except ValueError as exc:
            raise InvalidRequest("Choose a supported natural hazard.") from exc
    if not isinstance(data.avoid_repetition, bool) or not isinstance(
        data.disclose_area_to_provider, bool
    ):
        raise InvalidRequest("Subscription preferences must be enabled or disabled.")
    try:
        ReportRequest(
            template_id=data.template_id,
            question=data.question,
            research_mode=data.research_mode,
            research_focus=data.research_focus,
            country_iso=data.country_iso,
            country_isos=data.country_isos,
            conflict_id=data.conflict_id,
            hazard=data.hazard,
            plan_id=data.plan_id,
            research_area=data.research_area,
        )
    except ValueError as exc:
        raise InvalidRequest(str(exc)) from exc
