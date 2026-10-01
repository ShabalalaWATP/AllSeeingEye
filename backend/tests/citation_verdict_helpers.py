"""Synthetic saved reports with frozen citation checks for citation verdict tests."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.reports.citation_checks import check_report_citations
from ase.domain.citation_checks import ExcerptProposal
from ase.domain.teams import MembershipRole, Team, TeamMembership
from report_documents_helpers import document_records


async def seed_verdict_report(container, owner_id: UUID, *, team_id: UUID | None = None):
    container.clock.advance(timedelta(days=14))
    record, version = document_records(owner_id)
    record = replace(record, team_id=team_id)
    first = version.evidence[0]
    proposals = (ExcerptProposal("KJ1", first.label, "supporting", "title", first.title[:12]),)
    version = replace(
        version, citation_checks=check_report_citations(version.body, version.evidence, proposals)
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version, f"/api/reports/{record.id}/versions/1/citation-verdicts"


async def make_team(container, members, *, name="Verdict team"):
    team_id = uuid4()
    now = container.clock.now()
    async with container.session_factory() as session:
        teams = SqlTeamRepository(session)
        await teams.add(Team(team_id, name, True, members[0][0].id, now, now))
        for actor, role in members:
            await teams.put_membership(TeamMembership(team_id, actor.id, role, now))
        await session.commit()
    return team_id


MEMBER = MembershipRole.MEMBER


def verdict_payload(**changes):
    return {
        "judgement_id": "KJ1",
        "label": "E1",
        "relation": "supporting",
        "verdict": "supports",
        "note": "The excerpt states the reported movement directly.",
        **changes,
    }
