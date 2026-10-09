"""Explain report prerequisites using only inputs an alert rule actually retains."""

from collections.abc import Collection, Sequence
from uuid import UUID

from ase.application.reports.request import ReportRequest
from ase.application.reports.template_requirements import require_template_inputs
from ase.application.reports.templates import template_for
from ase.domain.errors import InvalidRequest


def require_alert_template(
    template_id: str | None,
    countries: Sequence[str],
    plan_id: UUID | None,
    templates: Collection[str],
) -> None:
    if template_id is None:
        return
    if template_id not in templates:
        message = "This report template is unavailable. Choose another template or No report."
        raise InvalidRequest(message, fields={"report_template": message})
    try:
        template = template_for(template_id)
        request = ReportRequest(
            template_id=template_id, country_isos=tuple(countries), plan_id=plan_id
        )
        require_template_inputs(template, request)
    except InvalidRequest as exc:
        field = next(iter(exc.fields or {}), "report_template")
        remedy = {
            "country": "Choose exactly one country, another template, or No report.",
            "question": (
                "Link a collection plan with a question, choose another template, or No report."
            ),
            "conflict": (
                "Alert rules cannot save a tracker conflict. Choose another template or No report."
            ),
            "hazard": (
                "Alert rules cannot save a tracker hazard. Choose another template or No report."
            ),
        }.get(field, "Choose another template or No report.")
        message = f"{exc.message} {remedy}"
        raise InvalidRequest(message, fields={"report_template": message}) from exc
