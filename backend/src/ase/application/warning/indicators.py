"""Indicators: any user creates them, the owner or an admin changes or removes them."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.direction import PlanRepository
from ase.application.ports.warning import IndicatorRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, InvalidRequest, NotFound
from ase.domain.events import BoundingBox, Category
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
    )


def _owner_or_admin(actor: User, indicator: Indicator) -> None:
    if indicator.created_by != actor.id and not actor.is_admin:
        raise Forbidden("Only the owner or an admin may change this indicator.")


class _IndicatorUseCase:
    def __init__(
        self,
        indicators: IndicatorRepository,
        plans: PlanRepository,
        templates: Collection[str],
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._indicators = indicators
        self._plans = plans
        self._templates = templates
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def _check_plan(self, plan_id: UUID | None) -> None:
        if plan_id is not None and await self._plans.get(plan_id) is None:
            raise InvalidRequest("Unknown collection plan.")

    async def _existing(self, actor: User, indicator_id: UUID) -> Indicator:
        indicator = await self._indicators.get(indicator_id)
        if indicator is None:
            raise NotFound("Indicator not found.")
        _owner_or_admin(actor, indicator)
        return indicator


class CreateIndicatorUseCase(_IndicatorUseCase):
    async def execute(
        self, actor: User, data: IndicatorInput, context: RequestContext
    ) -> Indicator:
        await self._check_plan(data.plan_id)
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
        await self._check_plan(data.plan_id)
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
    def __init__(self, indicators: IndicatorRepository) -> None:
        self._indicators = indicators

    async def execute(self, actor: User) -> list[Indicator]:
        return await self._indicators.list_all()
