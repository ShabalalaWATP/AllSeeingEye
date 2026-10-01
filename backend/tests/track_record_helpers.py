"""Bulk synthetic saved reports for source track record and research-quality tests.

Rows are inserted directly so a thousand-report population stays fast to build; every
value still passes through the domain codecs used by the report repository.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import update

from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.container import Container
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.report_records import (
    body_to_dict,
    evidence_to_list,
    findings_to_list,
    quality_to_dict,
)
from ase.domain.reports import ReportBody, ReportingItem, ReportingTheme
from ase.domain.teams import MembershipRole, Team, TeamMembership
from ase.domain.users import User
from ase.domain.validation_types import Finding
from evidence_matrix_helpers import item, judgement

SOURCE = "statistics-office"
Role = Literal["supporting", "contradicting", "elsewhere", "uncited", "absent"]


def cited_version(
    role: Role = "supporting", *, source_id: str = SOURCE, grade: str = "B2", others: int = 1
) -> tuple[ReportBody, tuple[EvidenceItem, ...]]:
    """One item from `source_id` (unless absent) plus `others` items from other sources."""
    extra = tuple(
        replace(item(f"E{index + 2}", "C3"), source_id=f"other-wire-{index}")
        for index in range(others)
    )
    other_labels = tuple(row.label for row in extra)
    mine = replace(item("E1", grade), source_id=source_id if role != "absent" else "other-desk")
    evidence = (mine, *extra)
    if role == "supporting":
        body = ReportBody(key_judgements=(judgement("E1", *other_labels),))
    elif role == "contradicting":
        body = ReportBody(key_judgements=(judgement(*other_labels, opposition=("E1",)),))
    elif role == "elsewhere":
        theme = ReportingTheme("Context", (ReportingItem("Background", ("E1",)),))
        body = ReportBody(key_judgements=(judgement(*other_labels),), reporting=(theme,))
    else:
        body = ReportBody(key_judgements=(judgement(*other_labels),))
    return body, evidence


def _version_row(
    report_id: UUID,
    number: int,
    created_at: datetime,
    body: ReportBody,
    evidence: tuple[EvidenceItem, ...],
    *,
    status: str,
    findings: tuple[Finding, ...] = (),
    analysis: dict[str, Any] | None = None,
    profile_id: UUID | None = None,
    model: str = "test-model",
    tokens: tuple[int | None, int | None] = (1200, 300),
) -> ReportVersionRow:
    return ReportVersionRow(
        id=uuid4(),
        report_id=report_id,
        number=number,
        status=status,
        body=body_to_dict(body),
        findings=findings_to_list(findings),
        evidence=evidence_to_list(evidence),
        quality=quality_to_dict(quality_of_information(evidence)),
        analysis=analysis,
        markdown="Synthetic saved report.",
        profile_id=profile_id,
        model=model,
        prompt_tokens=tokens[0],
        completion_tokens=tokens[1],
        latency_ms=10.0,
        attempts=1,
        created_at=created_at,
    )


async def insert_reports(
    container: Container,
    owner_id: UUID,
    count: int,
    *,
    start: datetime,
    team_id: UUID | None = None,
    status: str = "ready",
    role: Role = "supporting",
    source_id: str = SOURCE,
    grade: str = "B2",
    others: int = 1,
    template: str = "intsum",
    scope: dict[str, Any] | None = None,
    title: str = "Synthetic report",
    **version: Any,
) -> list[UUID]:
    """`count` reports, newest last, one saved version each, one minute apart from `start`."""
    body, evidence = cited_version(role, source_id=source_id, grade=grade, others=others)
    ids: list[UUID] = []
    async with container.session_factory() as session:
        for index in range(count):
            at = start + timedelta(minutes=index)
            report_id = uuid4()
            ids.append(report_id)
            session.add(
                ReportRow(
                    id=report_id,
                    team_id=team_id,
                    template=template,
                    title=f"{title} {index}",
                    scope=dict(scope or {}),
                    period_from=at - timedelta(days=1),
                    period_to=at,
                    data_cutoff=at,
                    status=status,
                    created_by=owner_id,
                    created_at=at,
                    latest_version=1,
                )
            )
            session.add(_version_row(report_id, 1, at, body, evidence, status=status, **version))
        await session.commit()
    return ids


async def add_version(
    container: Container,
    report_id: UUID,
    number: int,
    at: datetime,
    *,
    role: Role,
    status: str = "ready",
    **version: Any,
) -> None:
    body, evidence = cited_version(role)
    async with container.session_factory() as session:
        session.add(_version_row(report_id, number, at, body, evidence, status=status, **version))
        await session.execute(
            update(ReportRow)
            .where(ReportRow.id == report_id)
            .values(latest_version=number, status=status)
        )
        await session.commit()


async def add_team(
    container: Container, creator: User, members: list[tuple[User, MembershipRole]]
) -> UUID:
    team_id = uuid4()
    now = container.clock.now()
    async with container.session_factory() as session:
        teams = SqlTeamRepository(session)
        await teams.add(Team(team_id, f"Team {team_id.hex[:6]}", True, creator.id, now, now))
        for member, role in members:
            await teams.put_membership(TeamMembership(team_id, member.id, role, now))
        await session.commit()
    return team_id
