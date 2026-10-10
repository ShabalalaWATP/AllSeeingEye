"""Attach the original bounded evidence before the existing report job is frozen."""

from dataclasses import replace
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.alert_reports import SqlAlertReportQueue
from ase.application.model_routing import RoleProfiles
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.domain.errors import Forbidden
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.container import Container


async def prepare_alert_report(
    container: "Container", session: AsyncSession, actor: User, request: ReportRequest
) -> tuple[Job, RoleProfiles]:
    origin = request.alert_origin
    snapshot = await SqlAlertReportQueue(session).snapshot(origin.alert_id) if origin else None
    if snapshot is None or snapshot.origin != origin or origin is None:
        raise Forbidden()
    if (origin.owner_id, origin.team_id) != (actor.id, request.team_id):
        raise Forbidden()
    job, routing = await container.generate_report(session).prepare_job(
        actor, replace(request, alert_origin=None)
    )
    # A question template may obtain its question from the authorised collection plan.
    request = replace(request, question=job.request.question)
    return replace(
        job,
        request=request,
        scope={**job.scope, **report_scope(request, job.template)},
        reused_evidence=snapshot.evidence,
        background="\n\n".join(filter(None, (job.background, origin.describe()))),
    ), routing
