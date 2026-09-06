"""Frozen challenge metadata and actual production stages survive export and history."""

import io
import json
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from docx import Document
from pypdf import PdfReader

from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.reports.documents import ReportDocumentRenderer
from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_reports import ReportVersionOut
from ase.application.reports.archiving import archive_evidence
from ase.application.reports.document import build_document
from ase.application.reports.production import Producer
from ase.application.reports.render import render_markdown
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.challenge import ChallengeReview, ChallengeSearch, ReportChallenge
from ase.domain.challenge_records import challenge_from_dict, challenge_to_dict
from ase.domain.report_documents import ExportFormat
from ase.domain.report_records import analysis_to_dict
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchMode
from ase.domain.research_context import build_research_context
from feeds_helpers import make_event
from production_integration_helpers import RecordingUsage, production_job
from report_documents_helpers import document_records
from report_helpers import ScriptedGateway, filled_store, good_body


def challenge_records(owner=None):
    record, version = document_records(owner)
    challenge = ReportChallenge(
        (
            ChallengeSearch(
                "KJ1",
                "Original claim",
                ("contrary query",),
                "attempted",
                (CollectionAttempt("source", "Source", CollectionStatus.BUDGET_EXHAUSTED),),
            ),
        ),
        (
            ChallengeReview(
                "KJ1",
                "Final claim",
                "completed",
                DevilsAdvocacy(
                    "KJ1",
                    "A different explanation",
                    ("E3",),
                    rationale="Model rationale, unverified.",
                ),
            ),
        ),
        method_version="saved-challenge-v0",
    )
    return record, replace(
        version, challenge=challenge, research_context=build_research_context(version.evidence)
    )


def test_legacy_and_saved_challenge_do_not_recompute():
    _, legacy = document_records()
    _, version = challenge_records()
    assert ReportVersionOut.from_version(legacy).challenge is None
    assert challenge_from_dict(None) is None
    data = json.loads(json.dumps(challenge_to_dict(version.challenge)))
    assert challenge_from_dict(data) == version.challenge
    assert analysis_to_dict(version)["challenge"]["method_version"] == "saved-challenge-v0"


@pytest.mark.parametrize(
    "field,value",
    [("redrafted", "false"), ("request_limit", True), ("searches", "empty"), ("method_version", 3)],
)
def test_corrupt_saved_challenge_is_rejected(field, value):
    _, version = challenge_records()
    data = json.loads(json.dumps(challenge_to_dict(version.challenge)))
    data[field] = value
    with pytest.raises(ValueError):
        challenge_from_dict(data)


async def test_database_preserves_challenge_and_legacy_versions(container, user):
    record, version = challenge_records(user.id)
    old = replace(version, challenge=None, research_context=None)
    version = replace(version, id=uuid4(), number=2)
    record.latest_version = 2
    async with container.session_factory() as session:
        repo = SqlReportRepository(session)
        await repo.add(record, old)
        await repo.add_version(record, version)
        await session.commit()
    async with container.session_factory() as session:
        repo = SqlReportRepository(session)
        first = await repo.get_version(record.id, 1)
        second = await repo.get_version(record.id, 2)
        assert first.challenge is None
        assert second.challenge == version.challenge
        assert second.research_context == version.research_context


async def test_challenge_and_context_export_plain_text_and_archive_all_views():
    record, version = challenge_records()
    hostile = "<script>alert(1)</script> [bad](javascript:bad)"
    version = replace(
        version,
        challenge=replace(
            version.challenge,
            reviews=(
                replace(
                    version.challenge.reviews[0],
                    statement=hostile,
                ),
            ),
        ),
        evidence=tuple(replace(row, archive_url=None) for row in version.evidence),
    )
    markdown = render_markdown(
        record.header,
        version.body,
        version.evidence,
        version.quality,
        challenge=version.challenge,
        research_context=version.research_context,
    )
    doc = build_document(record, version)
    renderer = ReportDocumentRenderer()
    pdf = renderer.render(doc, ExportFormat.PDF)
    word = renderer.render(doc, ExportFormat.DOCX)
    pdf_text = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    word_text = " ".join(row.text for row in Document(io.BytesIO(word)).paragraphs)
    for text in (markdown, pdf_text, word_text):
        for expected in (
            "saved-challenge-v0",
            "budget exhausted",
            "contrarian view",
            "Recorded publication timeline",
            "Declared source chains",
        ):
            assert expected in text
    assert "<script>" not in markdown and "[bad](javascript" not in markdown
    assert hostile in word_text
    repo, archiver, uow = AsyncMock(), AsyncMock(), AsyncMock()
    repo.get.return_value = record
    archiver.archive.return_value = "https://example.org/snapshot"
    await archive_evidence(archiver, repo, uow, version)
    assert "saved-challenge-v0" in repo.set_archives.await_args.args[2]
    assert version.evidence[2].url in [call.args[0] for call in archiver.archive.await_args_list]


async def test_detailed_production_redrafts_with_new_evidence_before_all_reviews(container, user):
    job = production_job(user, container.cipher)
    job = replace(
        job,
        now=job.now + timedelta(hours=1),
        request=replace(job.request, research_mode=ResearchMode.DETAILED),
    )
    initial = good_body()
    changed = good_body(
        key_judgements=[
            {**row, "statement": row["statement"] + ""} for row in initial["key_judgements"]
        ]
    )
    plan = {
        "judgements": [
            {"target": row["id"], "terms": ["contrary observation"]}
            for row in initial["key_judgements"]
        ]
    }
    views = {
        "judgements": [
            {
                "target": row["id"],
                "argument": "A routine explanation remains.",
                "rationale": "Evidence is one-sided.",
                "evidence": ["E2"],
                "lower_confidence": True,
            }
            for row in initial["key_judgements"]
        ]
    }
    gateway = ScriptedGateway(
        json.dumps({"pir": "What changed?", "search_terms": []}),
        json.dumps(initial),
        json.dumps(plan),
        json.dumps(changed),
        json.dumps(views),
    )
    event = make_event(
        title="New contrary observation",
        source_id="new-source",
        observed_at=job.now,
        published_at=job.now - timedelta(minutes=1),
    )
    collection = AsyncMock()
    collection.collect.return_value = ResearchBatch()
    collection.challenge_many.return_value = (ResearchBatch(items=(event,)), ResearchBatch())
    usage = RecordingUsage()
    live = filled_store()
    producer = Producer(
        store=live,
        source_profiles={},
        cipher=container.cipher,
        gateway=gateway,
        usage=usage,
        research=collection,
        private_store_factory=InMemoryEventStore,
    )

    async def profile_for(role):
        return job.profile

    async def authorised():
        assert not usage.rows and len(gateway.requests) == 5

    version = await producer.produce(job, profile_for, authorised)
    assert [request.schema_name for request in gateway.requests] == [
        "direction",
        "report",
        "challenge_plan",
        "report",
        "challenge_reviews",
    ]
    assert version.challenge.redrafted
    assert len(version.challenge.reviews) == len(version.body.key_judgements) == 2
    assert version.advocacy.target == version.challenge.reviews[0].judgement_id
    assert version.research_context == build_research_context(version.evidence)
    assert "New contrary observation" in gateway.requests[3].messages[1].content
    assert "New contrary observation" in gateway.requests[4].messages[1].content
    assert live.get(event.id) is None
    assert len(usage.rows) == 5
