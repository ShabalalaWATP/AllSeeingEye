"""Current permissions and frozen configuration checks before durable work is used."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.application.model_routing import ModelRouting, RoleProfiles
from ase.application.report_jobs.collection_records import evidence_from_json
from ase.application.report_jobs.request_snapshot import request_from_dict
from ase.application.report_jobs.snapshots import restore_job
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.map_origin import ReportMapOrigin
from ase.application.reports.production_checkpoint import collection_from_dict
from ase.application.reports.production_types import Job
from ase.application.reports.research_inputs import ParentReference, require_parent
from ase.application.reports.templates import template_for
from ase.domain.errors import InvalidRequest
from ase.domain.model_routing_records import routing_to_dict
from ase.domain.report_jobs import ReportJob
from ase.domain.web_research import WEB_SOURCE_ID

if TYPE_CHECKING:
    from ase.container import Container


class ReportJobChanged(InvalidRequest):
    code = "report_job_configuration_changed"
    default_message = "The model configuration changed. Start a new report with the new settings."


class ReportJobSourceDisabled(InvalidRequest):
    code = "report_job_source_disabled"
    default_message = "A source in this report is disabled. Its saved content cannot be used."


async def check_sources(container: "Container", stored: ReportJob) -> None:
    frozen = stored.payload.get("input")
    if frozen is None:
        return  # List projections release metadata only.
    evidence = evidence_from_json(frozen["evidence"])
    collection = stored.payload.get("collection")
    identifiers = {item.source_id for item in evidence}
    if collection is not None:
        snapshot = collection_from_dict(collection)
        identifiers.update(item.source_id for item in snapshot.selection.items)
        web = snapshot.receipt.web_research if snapshot.receipt else None
        if web is not None and (web.synthesis or web.citations or web.consulted_urls):
            identifiers.add(WEB_SOURCE_ID)
    if identifiers and not all(
        (await container.source_admission.enabled_many(tuple(identifiers))).values()
    ):
        raise ReportJobSourceDisabled()


async def check_job(
    container: "Container", session: AsyncSession, stored: ReportJob
) -> tuple[Job, RoleProfiles]:
    """Caller owns source/administration locks and releases them before external work."""
    access = container.access_policy(session)
    owner = (await access.background(stored.owner_id, stored.team_id)).actor
    frozen = stored.payload["input"]
    template = template_for(frozen["template_id"])
    repos = container.repositories(session)
    routing = await ModelRouting(repos.llm_profiles, repos.llm_bindings).snapshot(
        team_id=stored.team_id,
        personal_owner_id=stored.owner_id,
        role=template.role,
        profile_id=UUID(frozen["request"]["profile_id"])
        if frozen["request"]["profile_id"]
        else None,
    )
    if routing_to_dict(routing.provenance) != frozen["routing"]:
        raise ReportJobChanged()
    job = restore_job(frozen, owner, routing.required(template.role))
    await check_links(container, session, stored, job)
    await check_sources(container, stored)
    return job, routing


async def release_job(container: "Container", session: AsyncSession, stored: ReportJob) -> None:
    """Saved drafts remain inspectable after a model change, subject to current access."""
    frozen = stored.payload.get("input")
    if frozen is None:
        return
    access, repos = container.access_policy(session), container.repositories(session)
    owner = (await access.background(stored.owner_id, stored.team_id)).actor
    template = template_for(frozen["template_id"])
    request = request_from_dict(frozen["request"], frozen["scope"], template)
    origin = ReportMapOrigin(access, repos.reports, repos.map_views)
    await ReportAuthorisation(
        access, repos.reports, repos.plans, repos.aois, repos.uow, origin
    ).prepare(owner, request)
    await origin.resolve(owner, request, owner_id=stored.owner_id)
    if request.parent_report_id is not None and request.parent_version is not None:
        await require_parent(
            access,
            repos.reports,
            owner,
            request,
            ParentReference(request.parent_report_id, request.parent_version, stored.owner_id),
        )
    await check_sources(container, stored)


async def check_links(
    container: "Container", session: AsyncSession, stored: ReportJob, job: Job
) -> None:
    access, repos = container.access_policy(session), container.repositories(session)
    origin = ReportMapOrigin(access, repos.reports, repos.map_views)
    authorisation = ReportAuthorisation(
        access, repos.reports, repos.plans, repos.aois, repos.uow, origin
    )
    plan = await authorisation.prepare(job.actor, job.request)
    if plan is not None and job.scope.get("collection_plan_revision") != {
        "id": str(plan.id),
        "updated_at": plan.updated_at.isoformat(),
    }:
        raise InvalidRequest("The collection plan changed. Start a new report.")
    await origin.resolve(job.actor, job.request, owner_id=stored.owner_id)
    if job.request.parent_report_id is not None and job.request.parent_version is not None:
        await require_parent(
            access,
            repos.reports,
            job.actor,
            job.request,
            ParentReference(
                job.request.parent_report_id, job.request.parent_version, stored.owner_id
            ),
        )
