"""A finished personal report version carrying every identity-dependent reference."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from ase.application.reports.source_assessment_projection import capture_unassessed_report_sources
from ase.domain.claim_generation import ClaimGenerationReceipt, ClaimGenerationStatus
from ase.domain.evidence_attributes import EvidenceAttribute
from ase.domain.original_followup import OriginalFollowupReceipt
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_records import ResearchReceipt
from ase.domain.teams import MembershipRole
from feeds_helpers import NOW
from report_documents_helpers import document_records
from team_helpers import CONTEXT, team_service

PRIVATE_LABEL = "E2"


def private_version(
    owner: UUID, *, private_input: bool = True
) -> tuple[ReportRecord, ReportVersion]:
    record, version = document_records(owner)
    evidence = list(version.evidence)
    if private_input:
        evidence[1] = replace(
            evidence[1],
            source_id="research_import",
            source_name="Private uploaded input",
            attributes=(
                EvidenceAttribute("filename", "field-notes.pdf"),
                EvidenceAttribute("media_type", "application/pdf"),
                EvidenceAttribute("original_sha256", "a" * 64),
            ),
        )
    first = evidence[0]
    research = ResearchReceipt(
        question="What is changing?",
        mode="quick",
        focus="general",
        languages=("en",),
        terms=("roads",),
        since=NOW - timedelta(days=2),
        until=NOW,
        attempts=(),
        collected_items=len(evidence),
        original_followup=(
            OriginalFollowupReceipt(
                first.label,
                first.event_id,
                first.source_id,
                "acquired",
                "original_passage_staged",
                passage_ref=uuid4(),
                passage_id="b" * 64,
                document_version_id="c" * 64,
                transport_requests=1,
            ),
        ),
    )
    frozen = replace(
        version,
        evidence=tuple(evidence),
        research=research,
        brief_id=uuid4(),
        brief_revision=2,
        claim_generation=ClaimGenerationReceipt(ClaimGenerationStatus.NO_MODEL),
        canonical_requirements=(IntelligenceRequirement("ir-1", "What is changing?"),),
        status=record.status,
    )
    frozen = replace(
        frozen,
        source_assessment=capture_unassessed_report_sources(
            frozen.id, frozen.body, frozen.evidence, frozen_at=NOW
        ),
    )
    scoped = replace(
        record,
        scope={
            "origin": "research",
            "question": "What is changing?",
            "report_language": "en",
            "plan": str(uuid4()),
            "parent_report_id": str(uuid4()),
            "parent_version": 1,
            "research_input": {"filename": "field-notes.pdf"},
            "unrecognised_future_key": "kept private",
        },
    )
    return scoped, frozen


async def seed_personal(container, owner_id, *, private_input=True, status=None):
    record, version = private_version(owner_id, private_input=private_input)
    if status is not None:
        record, version = replace(record, status=status), replace(version, status=status)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


async def team_with(container, admin, *members, name="Analysis desk"):
    async with team_service(container) as service:
        team = await service.create(admin, name, CONTEXT)
    for member in members:
        async with team_service(container) as service:
            await service.set_member(
                admin, team.id, email=member.email, role=MembershipRole.MEMBER, context=CONTEXT
            )
    return team


async def count(container, statement):
    async with container.session_factory() as session:
        return int(await session.scalar(statement) or 0)
