"""Collection plans and evidence are restricted to their personal or team scope."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.direction.plan_inputs import (
    PirInput,
    PlanInput,
    SirInput,
    plan_from_input,
    validate_plan_input,
)
from ase.application.direction.plan_updates import GetPlanUseCase, UpdatePlanUseCase
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.cooperative_feeds import CooperativeEventReader
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.application.ports.feeds import EventQuery, EventStore
from ase.domain.audit import AuditAction
from ase.domain.collection import (
    AreaOfInterest,
    CollectionPlan,
    in_scope,
    plan_matches,
)
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.events import Event
from ase.domain.evidence_time import publication_order
from ase.domain.users import User

# Existing callers and the container import plan inputs and editing from this module.
__all__ = [
    "CreatePlanUseCase",
    "DeletePlanUseCase",
    "GetPlanUseCase",
    "ListPlansUseCase",
    "PirInput",
    "PlanEvidence",
    "PlanEvidenceUseCase",
    "PlanInput",
    "SirEvidence",
    "SirInput",
    "UpdatePlanUseCase",
]

EVIDENCE_WINDOW = timedelta(days=7)
POOL = 5_000
PER_SIR = 30


@dataclass(frozen=True, slots=True)
class SirEvidence:
    code: str
    text: str
    events: tuple[Event, ...]


@dataclass(frozen=True, slots=True)
class PlanEvidence:
    plan: CollectionPlan
    aoi: AreaOfInterest | None
    considered: int
    sirs: tuple[SirEvidence, ...]


class CreatePlanUseCase:
    def __init__(
        self,
        plans: PlanRepository,
        aois: AoiRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
    ) -> None:
        self._plans, self._aois, self._clock, self._auditor, self._uow = (
            plans,
            aois,
            clock,
            auditor,
            uow,
        )
        self._access = access

    async def execute(
        self, actor: User, data: PlanInput, context: RequestContext
    ) -> CollectionPlan:
        decision = await self._access.context(actor, for_update=True)
        decision.require_create(data.team_id)
        name, _ = await validate_plan_input(data, self._aois, decision, actor.id)
        now = self._clock.now()
        plan = plan_from_input(data, name, uuid4(), actor.id, now, now)
        await self._plans.add(plan)
        await self._auditor.record(
            AuditAction.PLAN_CREATED, actor=actor.id, subject=str(plan.id), ip=context.ip,
            details={"name": plan.name, "pirs": len(plan.pirs)},
        )  # fmt: skip
        await self._uow.commit()
        return plan


class ListPlansUseCase:
    def __init__(self, plans: PlanRepository, access: AccessPolicy) -> None:
        self._plans = plans
        self._access = access

    async def execute(self, actor: User) -> list[CollectionPlan]:
        decision = await self._access.context(actor)
        return await self._plans.list_visible(decision.visibility)


class DeletePlanUseCase:
    def __init__(
        self, plans: PlanRepository, auditor: Auditor, uow: UnitOfWork, access: AccessPolicy
    ) -> None:
        self._plans, self._auditor, self._uow = plans, auditor, uow
        self._access = access

    async def execute(self, actor: User, plan_id: UUID, context: RequestContext) -> None:
        decision = await self._access.context(actor, for_update=True)
        plan = await self._plans.get(plan_id)
        if plan is None:
            raise NotFound()
        decision.require_write(plan.created_by, plan.team_id)
        await self._plans.delete(plan_id)
        await self._auditor.record(
            AuditAction.PLAN_DELETED, actor=actor.id, subject=str(plan_id), ip=context.ip
        )
        await self._uow.commit()


class PlanEvidenceUseCase:
    """What the live store holds against each requirement of a plan, right now."""

    def __init__(
        self,
        plans: PlanRepository,
        aois: AoiRepository,
        store: EventStore,
        clock: Clock,
        access: AccessPolicy,
    ) -> None:
        self._plans, self._aois, self._store, self._clock = plans, aois, store, clock
        self._access = access

    async def _scope(
        self, actor: User, plan_id: UUID
    ) -> tuple[CollectionPlan, AreaOfInterest | None]:
        decision = await self._access.context(actor)
        plan = await self._plans.get(plan_id)
        if plan is None:
            raise NotFound()
        decision.require_read(plan.created_by, plan.team_id)
        aoi = await self._aois.get(plan.aoi_id) if plan.aoi_id is not None else None
        if plan.aoi_id is not None and aoi is None:
            raise InvalidRequest("The linked area is unavailable; repair the plan before use.")
        if aoi is not None:
            decision.require_same_scope(plan.created_by, plan.team_id, aoi.created_by, aoi.team_id)
        return plan, aoi

    async def execute(self, actor: User, plan_id: UUID) -> PlanEvidence:
        plan, aoi = await self._scope(actor, plan_id)
        now = self._clock.now()
        if (
            aoi is not None
            and aoi.research_area is not None
            and isinstance(self._store, CooperativeEventReader)
        ):
            result = await self._store.read_cooperatively(
                EventQuery(
                    research_area=aoi.research_area, since=now - EVIDENCE_WINDOW, limit=POOL
                ),
                lambda events: self._evidence(plan, aoi, events),
                admission_key=f"user:{actor.id}",
            )
            # Worker admission yields. Recheck access and the selected records before return.
            if await self._scope(actor, plan_id) != (plan, aoi):
                raise InvalidRequest("The collection plan or area changed. Refresh its evidence.")
            return result
        pool = self._pool(plan, aoi, now)
        return self._evidence(plan, aoi, pool)

    @staticmethod
    def _evidence(
        plan: CollectionPlan, aoi: AreaOfInterest | None, pool: list[Event]
    ) -> PlanEvidence:
        matched: dict[str, list[Event]] = {sir.code: [] for sir in plan.sirs}
        for event in pool:
            if not in_scope(plan, aoi, event):
                continue
            for code in plan_matches(plan, event):
                if len(matched[code]) < PER_SIR:
                    matched[code].append(event)
        return PlanEvidence(
            plan=plan,
            aoi=aoi,
            considered=len(pool),
            sirs=tuple(
                SirEvidence(code=sir.code, text=sir.text, events=tuple(matched[sir.code]))
                for sir in plan.sirs
            ),
        )

    def _pool(self, plan: CollectionPlan, aoi: AreaOfInterest | None, now: datetime) -> list[Event]:
        since = now - EVIDENCE_WINDOW
        queries: list[EventQuery] = []
        if aoi is not None and aoi.research_area is not None:
            queries.append(EventQuery(research_area=aoi.research_area, since=since, limit=POOL))
        elif aoi is not None and aoi.kind == "bbox":
            queries.append(EventQuery(bbox=aoi.bbox, since=since, limit=POOL))
        countries = aoi.countries if aoi is not None and aoi.kind == "countries" else plan.countries
        queries.extend(EventQuery(country_iso=iso, since=since, limit=POOL) for iso in countries)
        if not queries:
            queries.append(EventQuery(since=since, limit=POOL))
        seen: dict[str, Event] = {}
        for query in queries:
            for event in self._store.query(query):
                seen.setdefault(event.id, event)
        return sorted(seen.values(), key=publication_order, reverse=True)
