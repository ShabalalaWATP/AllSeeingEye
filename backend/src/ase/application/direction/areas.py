"""Personal/team areas of interest with authoritative read and mutation policy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.direction import AoiRepository
from ase.domain.audit import AuditAction
from ase.domain.collection import AREA_KINDS, AreaOfInterest
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.events import BoundingBox
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class AoiInput:
    name: str
    kind: str
    bbox: tuple[float, float, float, float] | None = None
    countries: Sequence[str] = ()
    description: str = ""
    team_id: UUID | None = None


def build_area(data: AoiInput, actor: User, aoi_id: UUID, now: datetime) -> AreaOfInterest:
    """Validate the shape of an area before it is stored."""
    name = " ".join(data.name.split())
    if not name:
        raise InvalidRequest("An area needs a name.")
    if data.kind not in AREA_KINDS:
        raise InvalidRequest("An area is a bounding box or a set of nations.")
    bbox: BoundingBox | None = None
    countries = tuple(
        dict.fromkeys(code.strip().upper() for code in data.countries if code.strip())
    )
    if data.kind == "bbox":
        if data.bbox is None:
            raise InvalidRequest("A bounding box needs west, south, east and north.")
        west, south, east, north = data.bbox
        if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
            raise InvalidRequest("The bounding box is out of range.")
        bbox = BoundingBox(west=west, south=south, east=east, north=north)
    elif not countries:
        raise InvalidRequest("A nation area needs at least one nation.")
    return AreaOfInterest(
        id=aoi_id,
        name=name[:120],
        kind=data.kind,
        bbox=bbox,
        countries=countries,
        created_by=actor.id,
        created_at=now,
        description=" ".join(data.description.split())[:1000],
        team_id=data.team_id,
    )


class CreateAoiUseCase:
    def __init__(
        self,
        aois: AoiRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
    ) -> None:
        self._aois = aois
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._access = access

    async def execute(self, actor: User, data: AoiInput, context: RequestContext) -> AreaOfInterest:
        decision = await self._access.context(actor, for_update=True)
        decision.require_create(data.team_id)
        area = build_area(data, actor, uuid4(), self._clock.now())
        await self._aois.add(area)
        await self._auditor.record(
            AuditAction.AOI_CREATED, actor=actor.id, subject=str(area.id), ip=context.ip,
            details={"name": area.name, "kind": area.kind},
        )  # fmt: skip
        await self._uow.commit()
        return area


class ListAoisUseCase:
    def __init__(self, aois: AoiRepository, access: AccessPolicy) -> None:
        self._aois = aois
        self._access = access

    async def execute(self, actor: User) -> list[AreaOfInterest]:
        decision = await self._access.context(actor)
        return await self._aois.list_visible(decision.visibility)


class DeleteAoiUseCase:
    def __init__(
        self, aois: AoiRepository, auditor: Auditor, uow: UnitOfWork, access: AccessPolicy
    ) -> None:
        self._aois = aois
        self._auditor = auditor
        self._uow = uow
        self._access = access

    async def execute(self, actor: User, aoi_id: UUID, context: RequestContext) -> None:
        decision = await self._access.context(actor, for_update=True)
        area = await self._aois.get(aoi_id)
        if area is None:
            raise NotFound()
        decision.require_write(area.created_by, area.team_id)
        await self._aois.delete(aoi_id)
        await self._auditor.record(
            AuditAction.AOI_DELETED, actor=actor.id, subject=str(aoi_id), ip=context.ip
        )
        await self._uow.commit()
