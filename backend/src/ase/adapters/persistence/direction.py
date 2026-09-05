"""Repositories for areas of interest and collection plans (plans keep their PIRs as JSON)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import AoiRow, CollectionPlanRow
from ase.domain.collection import AreaOfInterest, CollectionPlan, Pir, Sir
from ase.domain.errors import NotFound
from ase.domain.events import BoundingBox, Category


def _aoi_from_row(row: AoiRow) -> AreaOfInterest:
    bbox = None
    if (
        row.west is not None
        and row.south is not None
        and row.east is not None
        and row.north is not None
    ):
        bbox = BoundingBox(west=row.west, south=row.south, east=row.east, north=row.north)
    return AreaOfInterest(
        id=row.id,
        name=row.name,
        kind=row.kind,
        bbox=bbox,
        countries=tuple(str(code) for code in row.countries),
        created_by=row.created_by,
        created_at=row.created_at,
        description=row.description,
    )


def pirs_to_list(pirs: tuple[Pir, ...]) -> list[dict[str, Any]]:
    return [
        {
            "code": pir.code,
            "text": pir.text,
            "sirs": [
                {
                    "code": sir.code,
                    "text": sir.text,
                    "keywords": list(sir.keywords),
                    "categories": [category.value for category in sir.categories],
                }
                for sir in pir.sirs
            ],
        }
        for pir in pirs
    ]


def pirs_from_list(items: list[Any]) -> tuple[Pir, ...]:
    return tuple(
        Pir(
            code=str(pir.get("code", "")),
            text=str(pir.get("text", "")),
            sirs=tuple(
                Sir(
                    code=str(sir.get("code", "")),
                    text=str(sir.get("text", "")),
                    keywords=tuple(str(k) for k in sir.get("keywords", [])),
                    categories=tuple(Category(str(c)) for c in sir.get("categories", [])),
                )
                for sir in pir.get("sirs", [])
            ),
        )
        for pir in items
        if isinstance(pir, dict)
    )


def _plan_from_row(row: CollectionPlanRow) -> CollectionPlan:
    return CollectionPlan(
        id=row.id,
        name=row.name,
        description=row.description,
        aoi_id=row.aoi_id,
        countries=tuple(str(code) for code in row.countries),
        pirs=pirs_from_list(list(row.pirs)),
        enabled=row.enabled,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _apply_plan(row: CollectionPlanRow, plan: CollectionPlan) -> None:
    row.name = plan.name
    row.description = plan.description
    row.aoi_id = plan.aoi_id
    row.countries = list(plan.countries)
    row.pirs = pirs_to_list(plan.pirs)
    row.enabled = plan.enabled
    row.created_by = plan.created_by
    row.created_at = plan.created_at
    row.updated_at = plan.updated_at


class SqlAoiRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, aoi: AreaOfInterest) -> None:
        self._session.add(
            AoiRow(
                id=aoi.id,
                name=aoi.name,
                description=aoi.description,
                kind=aoi.kind,
                west=aoi.bbox.west if aoi.bbox else None,
                south=aoi.bbox.south if aoi.bbox else None,
                east=aoi.bbox.east if aoi.bbox else None,
                north=aoi.bbox.north if aoi.bbox else None,
                countries=list(aoi.countries),
                created_by=aoi.created_by,
                created_at=aoi.created_at,
            )
        )
        await self._session.flush()

    async def get(self, aoi_id: UUID) -> AreaOfInterest | None:
        row = await self._session.get(AoiRow, aoi_id)
        return _aoi_from_row(row) if row else None

    async def list_all(self) -> list[AreaOfInterest]:
        rows = await self._session.scalars(select(AoiRow).order_by(AoiRow.name))
        return [_aoi_from_row(row) for row in rows]

    async def delete(self, aoi_id: UUID) -> None:
        await self._session.execute(delete(AoiRow).where(AoiRow.id == aoi_id))
        await self._session.flush()


class SqlPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, plan: CollectionPlan) -> None:
        row = CollectionPlanRow(id=plan.id)
        _apply_plan(row, plan)
        self._session.add(row)
        await self._session.flush()

    async def get(self, plan_id: UUID) -> CollectionPlan | None:
        row = await self._session.get(CollectionPlanRow, plan_id)
        return _plan_from_row(row) if row else None

    async def list_all(self) -> list[CollectionPlan]:
        rows = await self._session.scalars(
            select(CollectionPlanRow).order_by(CollectionPlanRow.created_at)
        )
        return [_plan_from_row(row) for row in rows]

    async def save(self, plan: CollectionPlan) -> None:
        row = await self._session.get(CollectionPlanRow, plan.id)
        if row is None:
            raise NotFound()
        _apply_plan(row, plan)
        await self._session.flush()

    async def delete(self, plan_id: UUID) -> None:
        await self._session.execute(
            delete(CollectionPlanRow).where(CollectionPlanRow.id == plan_id)
        )
        await self._session.flush()
