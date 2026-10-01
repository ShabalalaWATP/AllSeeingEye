"""Collection plan input and the validation shared by creating and editing a plan."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.ports.direction import AoiRepository
from ase.domain.collection import AreaOfInterest, CollectionPlan, numbered
from ase.domain.errors import InvalidRequest
from ase.domain.events import Category


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
    team_id: UUID | None = None


async def validate_plan_input(
    data: PlanInput, aois: AoiRepository, decision: AccessContext, owner: UUID
) -> tuple[str, AreaOfInterest | None]:
    name = " ".join(data.name.split())
    if not name:
        raise InvalidRequest("A plan needs a name.")
    if not data.pirs or not any(pir.text.strip() for pir in data.pirs):
        raise InvalidRequest("A plan needs at least one priority intelligence requirement.")
    # Blank groups would otherwise vanish silently and shift every later requirement code.
    if any(not pir.text.strip() for pir in data.pirs):
        raise InvalidRequest("Each priority intelligence requirement needs text.")
    if any(not sir.text.strip() for pir in data.pirs for sir in pir.sirs):
        raise InvalidRequest("Each specific intelligence requirement needs text.")
    aoi = None
    if data.aoi_id is not None:
        aoi = await aois.get(data.aoi_id)
        if aoi is None:
            raise InvalidRequest("Unknown area of interest.")
        decision.require_same_scope(owner, data.team_id, aoi.created_by, aoi.team_id)
    return name[:120], aoi


def plan_from_input(
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
        team_id=data.team_id,
    )
