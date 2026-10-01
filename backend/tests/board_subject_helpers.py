"""Seed scoped report, saved area and drawing records for board subject tests."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import update

from ase.adapters.persistence.map_workspace import SqlMapWorkspaceRepository
from ase.adapters.persistence.operational_models import ReportRow
from ase.container import Container
from ase.domain.collection import AreaOfInterest
from ase.domain.events import BoundingBox
from ase.domain.map_workspace import MapWorkspaceDocument
from feeds_helpers import NOW
from report_documents_helpers import document_records

DRAWINGS: dict[str, Any] = {"version": 1, "objects": [], "selectedId": None}


async def seed_report(
    container: Container, owner: UUID, team_id: UUID | str | None, title: str = "Team report"
) -> UUID:
    record, version = document_records(owner)
    item = replace(
        record,
        id=uuid4(),
        title=title,
        team_id=UUID(str(team_id)) if team_id is not None else None,
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(
            item, replace(version, id=uuid4(), report_id=item.id)
        )
        await session.commit()
    return item.id


async def move_report(container: Container, report_id: UUID, team_id: UUID | str | None) -> None:
    """Simulate a scope change outside the board, such as an operator correction."""
    async with container.session_factory() as session:
        await session.execute(
            update(ReportRow)
            .where(ReportRow.id == report_id)
            .values(team_id=UUID(str(team_id)) if team_id is not None else None)
        )
        await session.commit()


async def seed_area(
    container: Container, owner: UUID, team_id: UUID | str | None, name: str = "Team area"
) -> UUID:
    area = AreaOfInterest(
        uuid4(),
        name,
        "bbox",
        BoundingBox(30, 44, 41, 53),
        (),
        owner,
        NOW,
        team_id=UUID(str(team_id)) if team_id is not None else None,
    )
    async with container.session_factory() as session:
        await container.repositories(session).aois.add(area)
        await session.commit()
    return area.id


async def seed_document(
    container: Container,
    owner: UUID,
    team_id: UUID | str | None,
    title: str = "Team drawings",
    kind: str = "drawings",
) -> UUID:
    document = MapWorkspaceDocument(
        uuid4(),
        "drawings" if kind == "drawings" else "radio",
        title,
        DRAWINGS,
        1,
        owner,
        UUID(str(team_id)) if team_id is not None else None,
        NOW,
        NOW,
    )
    async with container.session_factory() as session:
        await SqlMapWorkspaceRepository(session).create(document)
        await session.commit()
    return document.id


def report_subject(report_id: UUID, version: int = 1) -> dict[str, Any]:
    return {"kind": "report_version", "id": str(report_id), "version": version}
