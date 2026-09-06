"""Check report ownership and linked collection scope before and after external work."""

from ase.application.access import AccessPolicy
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.application.ports.reports import ReportRepository
from ase.application.ports.repositories import UnitOfWork
from ase.application.reports.request import ReportRequest
from ase.domain.collection import CollectionPlan
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.report_records import ReportRecord
from ase.domain.users import User


class ReportAuthorisation:
    def __init__(
        self,
        access: AccessPolicy,
        reports: ReportRepository,
        plans: PlanRepository,
        aois: AoiRepository,
        uow: UnitOfWork,
    ) -> None:
        self._access, self._reports, self._plans = access, reports, plans
        self._aois, self._uow = aois, uow

    async def prepare(
        self,
        actor: User,
        request: ReportRequest,
        record: ReportRecord | None = None,
        *,
        for_update: bool = False,
    ) -> CollectionPlan | None:
        access = (
            await self._access.background(actor.id, request.team_id, for_update=for_update)
            if request.automation
            else await self._access.context(actor, for_update=for_update)
        )
        if record is None:
            access.require_create(request.team_id)
        else:
            access.require_write(record.created_by, record.team_id)
        if request.plan_id is None:
            return None
        plan = await self._plans.get(request.plan_id)
        if plan is None or not plan.pirs:
            raise NotFound()
        access.require_same_scope(
            record.created_by if record else actor.id,
            request.team_id,
            plan.created_by,
            plan.team_id,
        )
        if plan.aoi_id is not None:
            aoi = await self._aois.get(plan.aoi_id)
            if aoi is None:
                raise NotFound()
            access.require_same_scope(plan.created_by, plan.team_id, aoi.created_by, aoi.team_id)
        return plan

    async def finish(
        self,
        actor: User,
        request: ReportRequest,
        record: ReportRecord | None,
        plan: CollectionPlan | None,
    ) -> None:
        # No writes have started. End any read snapshot left by profile lookups before
        # acquiring the shared membership/account guard for the final atomic write.
        await self._uow.rollback()
        latest_plan = await self.prepare(actor, request, record, for_update=True)
        if plan is not None and (latest_plan is None or latest_plan.updated_at != plan.updated_at):
            raise InvalidRequest("The collection plan changed during generation. Try again.")
        if record is not None:
            latest = await self._reports.get(record.id)
            if latest is None:
                raise NotFound()
            if latest.latest_version != record.latest_version:
                raise InvalidRequest("Another version was saved during generation. Try again.")
