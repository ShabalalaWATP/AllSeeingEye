"""Collection plans: created by any user, edited by the owner or an admin, read by all."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.application.ports.feeds import EventQuery, EventStore
from ase.domain.audit import AuditAction
from ase.domain.collection import (
    AreaOfInterest,
    CollectionPlan,
    in_scope,
    numbered,
    plan_matches,
)
from ase.domain.errors import Forbidden, InvalidRequest, NotFound
from ase.domain.events import Category, Event
from ase.domain.users import User

EVIDENCE_WINDOW = timedelta(days=7)
POOL = 5_000
PER_SIR = 30


@dataclass(frozen=True, slots=True)
class SirInput:
    text: str
    keywords: Sequence[str] = ()
    categories: Sequence[Category] = ()


@dataclass(frozen=True, slots=True)
class PirInput:
    text: str
    sirs: Sequence[SirInput] = ()


@dataclass(frozen=True, slots=True)
class PlanInput:
    name: str
    description: str = ""
    aoi_id: UUID | None = None
    countries: Sequence[str] = ()
    pirs: Sequence[PirInput] = ()
    enabled: bool = True


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


async def _validated(data: PlanInput, aois: AoiRepository) -> tuple[str, AreaOfInterest | None]:
    name = " ".join(data.name.split())
    if not name:
        raise InvalidRequest("A plan needs a name.")
    if not data.pirs or not any(pir.text.strip() for pir in data.pirs):
        raise InvalidRequest("A plan needs at least one priority intelligence requirement.")
    aoi = None
    if data.aoi_id is not None:
        aoi = await aois.get(data.aoi_id)
        if aoi is None:
            raise InvalidRequest("Unknown area of interest.")
    return name[:120], aoi


def _plan_from(
    data: PlanInput,
    name: str,
    plan_id: UUID,
    owner: UUID,
    created: datetime,
    now: datetime,
) -> CollectionPlan:
    return CollectionPlan(
        id=plan_id,
        name=name,
        description=" ".join(data.description.split())[:2000],
        aoi_id=data.aoi_id,
        countries=tuple(dict.fromkeys(c.strip().upper() for c in data.countries if c.strip())),
        pirs=numbered(
            [
                (pir.text, [(sir.text, sir.keywords, sir.categories) for sir in pir.sirs])
                for pir in data.pirs
            ]
        ),
        enabled=data.enabled,
        created_by=owner,
        created_at=created,
        updated_at=now,
    )


class CreatePlanUseCase:
    def __init__(
        self,
        plans: PlanRepository,
        aois: AoiRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._plans, self._aois, self._clock, self._auditor, self._uow = (
            plans,
            aois,
            clock,
            auditor,
            uow,
        )

    async def execute(
        self, actor: User, data: PlanInput, context: RequestContext
    ) -> CollectionPlan:
        name, _ = await _validated(data, self._aois)
        now = self._clock.now()
        plan = _plan_from(data, name, uuid4(), actor.id, now, now)
        await self._plans.add(plan)
        await self._auditor.record(
            AuditAction.PLAN_CREATED, actor=actor.id, subject=str(plan.id), ip=context.ip,
            details={"name": plan.name, "pirs": len(plan.pirs)},
        )  # fmt: skip
        await self._uow.commit()
        return plan


class UpdatePlanUseCase:
    def __init__(
        self,
        plans: PlanRepository,
        aois: AoiRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._plans, self._aois, self._clock, self._auditor, self._uow = (
            plans,
            aois,
            clock,
            auditor,
            uow,
        )

    async def execute(
        self, actor: User, plan_id: UUID, data: PlanInput, context: RequestContext
    ) -> CollectionPlan:
        existing = await self._plans.get(plan_id)
        if existing is None:
            raise NotFound()
        if existing.created_by != actor.id and not actor.is_admin:
            raise Forbidden()
        name, _ = await _validated(data, self._aois)
        plan = _plan_from(
            data, name, plan_id, existing.created_by, existing.created_at, self._clock.now()
        )
        await self._plans.save(plan)
        await self._auditor.record(
            AuditAction.PLAN_UPDATED, actor=actor.id, subject=str(plan_id), ip=context.ip
        )
        await self._uow.commit()
        return plan


class ListPlansUseCase:
    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    async def execute(self, actor: User) -> list[CollectionPlan]:
        return await self._plans.list_all()


class DeletePlanUseCase:
    def __init__(self, plans: PlanRepository, auditor: Auditor, uow: UnitOfWork) -> None:
        self._plans, self._auditor, self._uow = plans, auditor, uow

    async def execute(self, actor: User, plan_id: UUID, context: RequestContext) -> None:
        plan = await self._plans.get(plan_id)
        if plan is None:
            raise NotFound()
        if plan.created_by != actor.id and not actor.is_admin:
            raise Forbidden()
        await self._plans.delete(plan_id)
        await self._auditor.record(
            AuditAction.PLAN_DELETED, actor=actor.id, subject=str(plan_id), ip=context.ip
        )
        await self._uow.commit()


class PlanEvidenceUseCase:
    """What the live store holds against each requirement of a plan, right now."""

    def __init__(
        self, plans: PlanRepository, aois: AoiRepository, store: EventStore, clock: Clock
    ) -> None:
        self._plans, self._aois, self._store, self._clock = plans, aois, store, clock

    async def execute(self, actor: User, plan_id: UUID) -> PlanEvidence:
        plan = await self._plans.get(plan_id)
        if plan is None:
            raise NotFound()
        aoi = await self._aois.get(plan.aoi_id) if plan.aoi_id is not None else None
        now = self._clock.now()
        pool = self._pool(plan, aoi, now)
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
        if aoi is not None and aoi.kind == "bbox":
            queries.append(EventQuery(bbox=aoi.bbox, since=since, limit=POOL))
        countries = aoi.countries if aoi is not None and aoi.kind == "countries" else plan.countries
        queries.extend(EventQuery(country_iso=iso, since=since, limit=POOL) for iso in countries)
        if not queries:
            queries.append(EventQuery(since=since, limit=POOL))
        seen: dict[str, Event] = {}
        for query in queries:
            for event in self._store.query(query):
                seen.setdefault(event.id, event)
        return sorted(seen.values(), key=lambda event: event.published_at, reverse=True)
