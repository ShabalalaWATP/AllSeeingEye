"""Personal and team indicators governed by current membership and write authority."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.direction import PlanRepository
from ase.application.ports.warning import IndicatorRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.events import BoundingBox, Category
from ase.domain.research_area import ResearchArea, validate_direct_area
from ase.domain.users import User
from ase.domain.warning import (
    MAX_COOLDOWN_MINUTES,
    MAX_KEYWORDS,
    MAX_THRESHOLD,
    MAX_WINDOW_MINUTES,
    MIN_WINDOW_MINUTES,
    Indicator,
)


@dataclass(frozen=True, slots=True)
class IndicatorInput:
    name: str
    description: str = ""
    plan_id: UUID | None = None
    countries: Sequence[str] = ()
    bbox: tuple[float, float, float, float] | None = None
    categories: Sequence[Category] = ()
    keywords: Sequence[str] = ()
    threshold: int = 1
    window_minutes: int = 60
    cooldown_minutes: int = 60
    severity_floor: float = 0.0
    report_template: str | None = None
    enabled: bool = True
    team_id: UUID | None = None
    research_area: ResearchArea | None = None


def _validate_area(data: IndicatorInput) -> None:
    if data.research_area is not None:
        try:
            validate_direct_area(data.research_area)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if data.bbox is not None or data.countries:
            raise InvalidRequest(
                "Choose an exact shape, a rectangle or nations, not several scopes."
            )
        if data.report_template is not None:
            raise InvalidRequest(
                "Exact-shape indicators support alerts only. "
                "Use an area research subscription for reports."
            )


def build_indicator(
    data: IndicatorInput,
    *,
    templates: Collection[str],
    indicator_id: UUID,
    owner: UUID,
    created: datetime,
    now: datetime,
) -> Indicator:
    name = " ".join(data.name.split())
    if not name:
        raise InvalidRequest("An indicator needs a name.")
    _validate_area(data)
    bbox: BoundingBox | None = None
    if data.bbox is not None:
        west, south, east, north = data.bbox
        if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
            raise InvalidRequest("The bounding box is out of range.")
        bbox = BoundingBox(west=west, south=south, east=east, north=north)
    keywords = tuple(dict.fromkeys(" ".join(w.split()) for w in data.keywords if w.strip()))
    if len(keywords) > MAX_KEYWORDS:
        raise InvalidRequest(f"At most {MAX_KEYWORDS} keywords.")
    if not (1 <= data.threshold <= MAX_THRESHOLD):
        raise InvalidRequest("The threshold must be between 1 and 10000.")
    if not (MIN_WINDOW_MINUTES <= data.window_minutes <= MAX_WINDOW_MINUTES):
        raise InvalidRequest("The window must be between 5 minutes and 7 days.")
    if not (1 <= data.cooldown_minutes <= MAX_COOLDOWN_MINUTES):
        raise InvalidRequest("The cooldown must be between 1 minute and 24 hours.")
    if not (0.0 <= data.severity_floor <= 1.0):
        raise InvalidRequest("The severity floor must be between 0 and 1.")
    if data.report_template is not None and data.report_template not in templates:
        raise InvalidRequest("Unknown report template.")
    return Indicator(
        id=indicator_id,
        name=name[:120],
        description=" ".join(data.description.split())[:1000],
        plan_id=data.plan_id,
        countries=tuple(dict.fromkeys(c.strip().upper() for c in data.countries if c.strip())),
        bbox=bbox,
        research_area=data.research_area,
        categories=tuple(dict.fromkeys(data.categories)),
        keywords=keywords,
        threshold=data.threshold,
        window_minutes=data.window_minutes,
        cooldown_minutes=data.cooldown_minutes,
        severity_floor=data.severity_floor,
        report_template=data.report_template,
        enabled=data.enabled,
        created_by=owner,
        created_at=created,
        updated_at=now,
        team_id=data.team_id,
    )


class _IndicatorUseCase:
    def __init__(
        self,
        indicators: IndicatorRepository,
        plans: PlanRepository,
        templates: Collection[str],
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
    ) -> None:
        self._indicators = indicators
        self._plans = plans
        self._templates = templates
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._access = access

    async def _check_plan(self, data: IndicatorInput, owner: UUID, access: AccessContext) -> None:
        if data.plan_id is None:
            return
        plan = await self._plans.get(data.plan_id)
        if plan is None:
            raise InvalidRequest("Unknown collection plan.")
        access.require_same_scope(owner, data.team_id, plan.created_by, plan.team_id)

    async def _existing(self, actor: User, indicator_id: UUID) -> Indicator:
        access = await self._access.context(actor, for_update=True)
        indicator = await self._indicators.get(indicator_id)
        if indicator is None:
            raise NotFound("Indicator not found.")
        access.require_write(indicator.created_by, indicator.team_id)
        return indicator


class CreateIndicatorUseCase(_IndicatorUseCase):
    async def execute(
        self, actor: User, data: IndicatorInput, context: RequestContext
    ) -> Indicator:
        access = await self._access.context(actor, for_update=True)
        access.require_create(data.team_id)
        await self._check_plan(data, actor.id, access)
        now = self._clock.now()
        indicator = build_indicator(
            data, templates=self._templates, indicator_id=uuid4(), owner=actor.id,
            created=now, now=now,
        )  # fmt: skip
        await self._indicators.add(indicator)
        await self._auditor.record(
            AuditAction.INDICATOR_CREATED, actor=actor.id, subject=str(indicator.id),
            ip=context.ip, details={"name": indicator.name},
        )  # fmt: skip
        await self._uow.commit()
        return indicator


class UpdateIndicatorUseCase(_IndicatorUseCase):
    async def execute(
        self, actor: User, indicator_id: UUID, data: IndicatorInput, context: RequestContext
    ) -> Indicator:
        existing = await self._existing(actor, indicator_id)
        if data.team_id != existing.team_id:
            raise InvalidRequest("An indicator's personal or team scope cannot be changed.")
        access = await self._access.context(actor)
        await self._check_plan(data, existing.created_by, access)
        indicator = build_indicator(
            data, templates=self._templates, indicator_id=existing.id,
            owner=existing.created_by, created=existing.created_at, now=self._clock.now(),
        )  # fmt: skip
        await self._indicators.save(indicator)
        await self._auditor.record(
            AuditAction.INDICATOR_UPDATED, actor=actor.id, subject=str(indicator.id),
            ip=context.ip, details={"name": indicator.name, "enabled": indicator.enabled},
        )  # fmt: skip
        await self._uow.commit()
        return indicator


class DeleteIndicatorUseCase(_IndicatorUseCase):
    async def execute(self, actor: User, indicator_id: UUID, context: RequestContext) -> None:
        indicator = await self._existing(actor, indicator_id)
        await self._indicators.delete(indicator.id)
        await self._auditor.record(
            AuditAction.INDICATOR_DELETED, actor=actor.id, subject=str(indicator.id),
            ip=context.ip, details={"name": indicator.name},
        )  # fmt: skip
        await self._uow.commit()


class ListIndicatorsUseCase:
    def __init__(self, indicators: IndicatorRepository, access: AccessPolicy) -> None:
        self._indicators = indicators
        self._access = access

    async def execute(self, actor: User) -> list[Indicator]:
        access = await self._access.context(actor)
        return await self._indicators.list_all(access.visibility)
