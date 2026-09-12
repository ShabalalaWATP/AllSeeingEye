"""Frozen citation checks and collection receipts survive every report representation."""

import io
import json
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from docx import Document
from httpx import AsyncClient
from pypdf import PdfReader

from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.reports.documents import ReportDocumentRenderer
from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_reports import ReportCreateIn, ReportVersionOut
from ase.application.reports.archiving import archive_evidence
from ase.application.reports.citation_checks import (
    check_generated_report_citations,
    check_report_citations,
)
from ase.application.reports.comparison import compare_versions
from ase.application.reports.document import build_document
from ase.application.reports.production import Producer
from ase.application.reports.render import render_markdown
from ase.application.reports.selection import Selection
from ase.application.reports.templates import TEMPLATES
from ase.container import Container
from ase.domain.citation_check_records import citation_checks_from_dict, citation_checks_to_dict
from ase.domain.citation_checks import CitationStatus
from ase.domain.report_documents import ExportFormat
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchMode
from ase.domain.research_records import ResearchReceipt
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from planning_integration_helpers import PlanningStageGateway, synthetic_plan
from production_integration_helpers import RecordingUsage, production_job
from report_documents_helpers import document_records
from report_helpers import filled_store


def frozen_records(owner=None):
    record, version = document_records(owner)
    statement = "We assess that Ukraine deployed 12 vehicles near Kharkiv on 4 September 2026."
    evidence = tuple(
        replace(
            item,
            summary=statement.replace("We assess that ", "").rstrip(".") + ", officials said.",
            language="en",
        )
        for item in version.evidence
    )
    first, second = version.body.key_judgements
    body = replace(
        version.body,
        key_judgements=(
            replace(first, statement=statement, supporting_evidence=("E1",)),
            replace(
                second,
                statement=statement.replace("12", "20"),
                supporting_evidence=("E2",),
                contradicting_evidence=("E999",),
            ),
        ),
    )
    receipt = ResearchReceipt(
        "What changed?",
        "quick",
        "general",
        ("en", "uk"),
        ("Харків",),
        record.period_from,
        record.period_to,
        (
            CollectionAttempt(
                "fixture", "Fixture source", CollectionStatus.COMPLETED, 3, "Feed queried.", "uk"
            ),
            CollectionAttempt(
                "unavailable",
                "Unavailable source",
                CollectionStatus.UNAVAILABLE,
                0,
                "No adapter configured.",
            ),
        ),
        3,
    )
    checks = replace(check_report_citations(body, evidence), method_version="saved-citation-v0")
    return record, replace(
        version, body=body, evidence=evidence, citation_checks=checks, research=receipt
    )


def test_legacy_report_does_not_invent_citation_checks_or_collection_coverage():
    record, version = document_records()
    assert version.citation_checks is None
    assert ReportVersionOut.from_version(version).model_dump()["citation_checks"] is None
    text = "\n".join(block.text for block in build_document(record, version).blocks)
    assert "citation checks" not in text.lower()
    assert "collection receipt" not in text.lower()


def test_citation_checks_roundtrip_exactly_and_reject_corrupt_types():
    _, version = frozen_records()
    payload = json.loads(json.dumps(citation_checks_to_dict(version.citation_checks)))
    assert citation_checks_from_dict(payload) == version.citation_checks
    assert citation_checks_from_dict(None) is None
    payload["judgements"][0]["citations"][0]["excerpt"]["start"] = True
    with pytest.raises(ValueError):
        citation_checks_from_dict(payload)


async def test_database_and_api_preserve_frozen_checks_receipts_and_legacy_absence(
    container: Container,
    client: AsyncClient,
    user: User,
):
    record, second = frozen_records(user.id)
    first = replace(second, citation_checks=None, research=None)
    second = replace(second, id=uuid4(), number=2)
    record.latest_version = 2
    async with container.session_factory() as session:
        repo = SqlReportRepository(session)
        await repo.add(record, first)
        await repo.add_version(record, second)
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    root = f"/api/reports/{record.id}"
    legacy = await client.get(root + "?version=1", headers=bearer(token))
    current = await client.get(root + "?version=2", headers=bearer(token))
    assert legacy.status_code == current.status_code == 200
    assert legacy.json()["version"]["citation_checks"] is None
    assert current.json()["version"]["citation_checks"] == json.loads(
        json.dumps(
            citation_checks_to_dict(second.citation_checks),
        )
    )
    async with container.session_factory() as session:
        stored = await SqlReportRepository(session).get_version(record.id, 2)
        assert stored.citation_checks == second.citation_checks
        assert stored.research == second.research


def test_reader_exports_hide_checks_receipts_and_untrusted_operational_text():
    record, version = frozen_records()
    hostile = "<script>alert(1)</script> [forged](javascript:alert(1))"
    version = replace(version, research=replace(version.research, question=hostile))
    markdown = render_markdown(
        record.header,
        version.body,
        version.evidence,
        version.quality,
        citation_checks=version.citation_checks,
        research=version.research,
    )
    document = build_document(record, version)
    renderer = ReportDocumentRenderer()
    word = Document(io.BytesIO(renderer.render(document, ExportFormat.DOCX)))
    pdf = PdfReader(io.BytesIO(renderer.render(document, ExportFormat.PDF)))
    operational_values = (
        "saved-citation-v0",
        "KJ1: literal citation checks",
        "KJ2: literal citation checks",
        "number mismatch",
        "Excerpt SHA-256",
        "Collection coverage",
        "3 additional items",
        "Unavailable source",
        "does not establish semantic entailment",
    )
    for value in operational_values:
        assert value in " ".join(markdown.split())
    for text in (
        "\n".join(row.text for row in word.paragraphs),
        "\n".join(page.extract_text() for page in pdf.pages),
    ):
        assert all(value not in " ".join(text.split()) for value in operational_values)
    assert "<script>" not in markdown and "[forged](javascript" not in markdown
    assert hostile not in "\n".join(block.text for block in document.blocks)


async def test_delayed_archival_keeps_saved_checks_and_collection_receipts():
    record, version = frozen_records()
    version = replace(
        version, evidence=tuple(replace(row, archive_url=None) for row in version.evidence)
    )
    repo, archiver, uow = AsyncMock(), AsyncMock(), AsyncMock()
    repo.get.return_value = record
    archiver.archive.return_value = "https://example.org/snapshot"
    await archive_evidence(archiver, repo, uow, version)
    markdown = repo.set_archives.await_args.args[2]
    assert "## References" in markdown
    assert "saved-citation-v0" not in markdown and "Unavailable source" not in markdown
    revised = replace(
        version,
        citation_checks=replace(version.citation_checks, method_version="saved-v1"),
        research=replace(version.research, collected_items=4),
    )
    assert {change.section for change in compare_versions(record, version, revised).changes} == {
        "Literal citation checks",
        "Collection coverage",
    }


def test_invalid_draft_or_long_source_keeps_explicit_unavailable_checks_without_regrading():
    _, version = frozen_records()
    body = replace(version.body, key_judgements=(version.body.key_judgements[0],) * 2)
    checks = check_generated_report_citations(body, version.evidence)
    assert len(checks.judgements) == 2
    assert all(row.status is CitationStatus.CONTEXT_INSUFFICIENT for row in checks.judgements)
    assert "must be unique" in checks.judgements[0].reasons[0]


@pytest.mark.parametrize("template", ["ask", "intsum", "country_brief"])
async def test_research_generation_freezes_checks_cutoff_receipt_and_missing_query_plan(
    container: Container,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
    template: str,
):
    job = production_job(user, container.cipher)
    job = replace(
        job,
        template=TEMPLATES[template],
        request=replace(
            job.request, research_mode=ResearchMode.QUICK, research_languages=("en", "uk")
        ),
    )
    _, sample = frozen_records()
    captured = job.now + timedelta(minutes=2)
    selection = Selection(
        tuple(replace(item, captured_at=captured) for item in sample.evidence), 0, 3
    )
    monkeypatch.setattr(
        "ase.application.reports.production_selection.select_evidence", lambda *a, **k: selection
    )
    collection = AsyncMock()
    collection.plan = synthetic_plan
    collection.collect.return_value = ResearchBatch(
        attempts=(
            CollectionAttempt(
                "fixture", "Fixture", CollectionStatus.EMPTY, explanation="No results."
            ),
        )
    )

    async def profile_for(role):
        return job.profile

    usage = RecordingUsage()
    gateway = PlanningStageGateway()
    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=gateway,
        usage=usage,
        research=collection,
        private_store_factory=InMemoryEventStore,
    )

    async def before_persist():
        assert not usage.rows

    version = await producer.produce(job, profile_for, before_persist)
    assert gateway.calls[0] == "direction"
    assert gateway.calls.count("research_plan") == 1
    assert any(row.purpose == "research:planning" and row.ok for row in usage.rows)
    assert version.citation_checks == check_report_citations(version.body, version.evidence)
    assert version.data_cutoff == captured
    assert (version.period_from, version.period_to) == (job.now - job.window, job.now)
    assert version.research is not None
    assert any(finding.rule == "research_query_plan" for finding in version.findings)
    assert version.markdown.count("## Executive summary") == 1
    assert "## References" in version.markdown
    assert "Collection coverage" not in version.markdown


@pytest.mark.parametrize("focus", ["company", "domain", "document", "media"])
def test_country_filter_is_rejected_for_record_focused_research(focus):
    with pytest.raises(ValueError, match="Country filters"):
        ReportCreateIn.model_validate(
            {
                "template": "intsum",
                "question": "What is known?",
                "research_mode": "quick",
                "research_focus": focus,
                "country": "GB",
            }
        )
