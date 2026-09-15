"""Current permissions and frozen configuration checks before durable work is used."""

from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.model_routing import ModelRouting, RoleProfiles
from ase.application.report_jobs.collection_records import evidence_from_json
from ase.application.report_jobs.snapshots import restore_job
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.map_origin import ReportMapOrigin
from ase.application.reports.production_checkpoint import collection_from_dict
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.application.reports.research_inputs import ParentReference, require_parent
from ase.application.reports.templates import template_for
from ase.domain.errors import InvalidRequest
from ase.domain.model_routing_records import routing_to_dict
from ase.domain.report_jobs import ReportJob
from ase.domain.report_records import ReportVersion
from ase.domain.users import User
from ase.domain.web_research import WEB_SOURCE_ID

if TYPE_CHECKING:
    from ase.container import Container


class ReportJobChanged(InvalidRequest):
    code = "report_job_configuration_changed"
    default_message = "The model configuration changed. Start a new report with the new settings."


class ReportJobSourceDisabled(InvalidRequest):
    code = "report_job_source_disabled"
    default_message = "A source in this report is disabled. Its saved content cannot be used."


async def check_sources(
    container: "Container", stored: ReportJob, baseline: ReportVersion | None = None
) -> None:
    frozen = stored.payload.get("input")
    if frozen is None:
        return  # List projections release metadata only.
    evidence = evidence_from_json(frozen["evidence"])
    collection = stored.payload.get("collection")
    identifiers = {item.source_id for item in evidence}
    if baseline is not None:
        identifiers.update(item.source_id for item in baseline.evidence)
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
    edition = await SqlSubscriptionEditionRepository(session).get_by_job(stored.id)
    if edition is not None:
        schedule = await session.get(ScheduleRow, edition.subscription_id, populate_existing=True)
        if schedule is None or schedule.archived_at is not None or not schedule.enabled:
            raise InvalidRequest("The subscription is inactive; its job cannot resume.")
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
    baseline = await _subscription_baseline(container, session, stored, owner, job.request)
    await check_sources(container, stored, baseline)
    if baseline is not None:
        job = replace(job, subscription_baseline=baseline)
    return job, routing


async def release_job(container: "Container", session: AsyncSession, stored: ReportJob) -> None:
    """Source gate for reads and pauses, which start no work.

    The service authorises the caller with ``require_read`` on the job. The owner's
    background authority is deliberately not required here: a deactivated owner or an
    archived team must not hide existing progress from an authorised reader. Admission
    and resume use ``check_job``, which does require it. The response exposes progress
    metadata only, so linked plans, areas and parent reports are not re-authorised.
    """
    frozen = stored.payload.get("input")
    if frozen is None:
        return
    baseline = None
    context = frozen.get("subscription_context")
    if context is not None and context["version"] is not None:
        # Only the baseline's source identifiers are used, never returned.
        baseline = await container.repositories(session).reports.get_version(
            UUID(context["report_id"]), context["version"]
        )
    await check_sources(container, stored, baseline)


async def _subscription_baseline(
    container: "Container",
    session: AsyncSession,
    stored: ReportJob,
    actor: User,
    request: ReportRequest,
) -> ReportVersion | None:
    frozen = stored.payload["input"]
    context = frozen.get("subscription_context")
    if context is None or context["version"] is None:
        return None
    return await require_parent(
        container.access_policy(session),
        container.repositories(session).reports,
        actor,
        request,
        ParentReference(UUID(context["report_id"]), context["version"], stored.owner_id),
    )


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
