"""Automated assessments are frozen with each version, never inferred for history."""

import io
import json
from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from docx import Document
from httpx import AsyncClient
from pypdf import PdfReader

from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.reports.documents import ReportDocumentRenderer
from ase.api.schemas_reports import ReportVersionOut
from ase.application.reports.archiving import archive_evidence
from ase.application.reports.assessment_export import assessment_sections
from ase.application.reports.comparison import compare_versions
from ase.application.reports.document import build_document
from ase.application.reports.production import Producer
from ase.application.reports.render import render_markdown
from ase.container import Container
from ase.domain.evidence_matrix import evidence_policy_metadata
from ase.domain.judgement_assessment import build_report_assessment
from ase.domain.report_assessment_records import assessment_from_dict, assessment_to_dict
from ase.domain.report_documents import ExportFormat
from ase.domain.report_records import analysis_to_dict
from ase.domain.reports import ReportStatus
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from production_integration_helpers import RecordingUsage, StageGateway, production_job
from report_documents_helpers import document_records
from report_helpers import ScriptedGateway, filled_store


def test_legacy_version_has_no_invented_assessment() -> None:
    _, version = document_records()
    assert version.assessment is None
    assert ReportVersionOut.from_version(version).model_dump()["assessment"] is None
    assert "assessment" not in (analysis_to_dict(version) or {})


async def test_report_methodology_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/report-methodology")).status_code == 401


def test_saved_assessment_roundtrip_preserves_method_and_exact_results() -> None:
    _, version = document_records()
    evidence = (
        replace(version.evidence[0], independence_key="Declared agency"),
        *version.evidence[1:],
    )
    assessment = build_report_assessment(version.body, evidence, version.findings)
    frozen = replace(assessment, method_version="saved-policy-v0")
    payload = json.loads(json.dumps(assessment_to_dict(frozen)))
    assert assessment_from_dict(payload) == frozen
    assert assessment_from_dict(None) is None
    saved = json.loads(json.dumps(analysis_to_dict(replace(version, assessment=frozen))))
    assert saved["assessment"] == payload


@pytest.mark.parametrize(
    "field,value",
    [
        ("validation_errors", True),
        ("method_version", 12),
        ("limitations", "none"),
        ("validation_warnings", "0"),
    ],
)
def test_corrupt_saved_assessment_does_not_coerce_or_regrade(field, value) -> None:
    _, version = document_records()
    assessment = build_report_assessment(version.body, version.evidence, version.findings)
    payload = json.loads(json.dumps(assessment_to_dict(assessment)))
    payload[field] = value
    with pytest.raises(ValueError):
        assessment_from_dict(payload)


async def test_methodology_matches_domain_policy_and_preserves_separate_yardstick(
    client: AsyncClient,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/report-methodology", headers=bearer(token))
    assert response.status_code == 200, response.text
    payload = response.json()
    for key, value in evidence_policy_metadata().items():
        assert payload[key] == value
    assert len(payload["contribution_matrix"]) == 36
    assert len(payload["probability_yardstick"]) == 7
    assert payload["probability_yardstick"][0]["term"] == "remote chance"
    ranges = [band["range_description"] for band in payload["probability_yardstick"]]
    assert "above 0" in ranges[0].lower()
    assert "under 50" in ranges[3].lower()
    assert "under 100" in ranges[-1].lower()


async def test_sql_and_api_keep_each_versions_assessment_and_legacy_absence(
    container: Container,
    client: AsyncClient,
    user: User,
) -> None:
    record, first = document_records(user.id)
    assessment = build_report_assessment(first.body, first.evidence, first.findings)
    second = replace(
        first,
        id=uuid4(),
        number=2,
        assessment=replace(
            assessment,
            method_version="saved-policy-v0",
        ),
    )
    record.latest_version = 2
    async with container.session_factory() as session:
        repository = SqlReportRepository(session)
        await repository.add(record, first)
        await repository.add_version(record, second)
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    root = f"/api/reports/{record.id}"
    old = await client.get(root + "?version=1", headers=bearer(token))
    new = await client.get(root + "?version=2", headers=bearer(token))
    assert old.status_code == new.status_code == 200
    assert old.json()["version"]["assessment"] is None
    assert new.json()["version"]["assessment"] == json.loads(
        json.dumps(
            assessment_to_dict(second.assessment),
        )
    )
    async with container.session_factory() as session:
        saved = await SqlReportRepository(session).get_version(record.id, 2)
        assert saved is not None and saved.assessment == second.assessment


def test_every_export_contains_the_same_frozen_assessment() -> None:
    record, version = document_records()
    assessment = build_report_assessment(version.body, version.evidence, version.findings)
    assessment = replace(assessment, method_version="saved-policy-v0")
    version = replace(version, assessment=assessment)
    markdown = render_markdown(
        record.header,
        version.body,
        version.evidence,
        version.quality,
        assessment=assessment,
    )
    document = build_document(record, version)
    renderer = ReportDocumentRenderer()
    word = Document(io.BytesIO(renderer.render(document, ExportFormat.DOCX)))
    pdf = PdfReader(io.BytesIO(renderer.render(document, ExportFormat.PDF)))
    texts = [
        markdown,
        "\n".join(p.text for p in word.paragraphs),
        " ".join(page.extract_text() for page in pdf.pages),
    ]
    for text in texts:
        normal = " ".join(text.split())
        assert "saved-policy-v0" in text
        assert "not an accuracy percentage" in normal
        assert "does not verify that citations support the claims" in normal
        assert "Source contributions:" in normal
        assert "support groups (model-assigned):" in normal
        assert "Improve:" in normal
    assert all(
        paragraph in [block.text for block in document.blocks]
        for _, paragraphs in assessment_sections(assessment)
        for paragraph in paragraphs
    )
    paragraphs = [paragraph for _, rows in assessment_sections(assessment) for paragraph in rows]
    for limitation in assessment.limitations:
        assert paragraphs.count(f"Limitation: {limitation}") == 1
    assert not any("Balance: support_only" in paragraph for paragraph in paragraphs)


async def test_late_archive_preserves_the_saved_assessment_and_version_comparison() -> None:
    record, version = document_records()
    assessment = replace(
        build_report_assessment(version.body, version.evidence, version.findings),
        method_version="saved-policy-v0",
    )
    version = replace(
        version,
        assessment=assessment,
        evidence=tuple(replace(item, archive_url=None) for item in version.evidence),
    )
    repository, archiver, uow = AsyncMock(), AsyncMock(), AsyncMock()
    repository.get.return_value = record
    archiver.archive.return_value = "https://example.org/snapshot"
    assert await archive_evidence(archiver, repository, uow, version) > 0
    assert "saved-policy-v0" in repository.set_archives.await_args.args[2]
    changed = replace(version, assessment=replace(assessment, method_version="saved-policy-v1"))
    comparison = compare_versions(record, version, changed)
    assert [(c.section, c.path, c.before, c.after) for c in comparison.changes] == [
        ("Automated evidence assessment", "method_version", "saved-policy-v0", "saved-policy-v1"),
    ]


async def test_production_assesses_final_body_before_late_authorisation_and_usage(
    container: Container,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    usage, gateway = RecordingUsage(), StageGateway()
    job = production_job(user, container.cipher)
    observed = []

    def assess(body, evidence, findings):
        assert gateway.calls == ["direction", "report", "advocacy"]
        assert usage.rows == []
        observed.append(body)
        return build_report_assessment(body, evidence, findings)

    async def before_persist():
        assert len(observed) == 1 and usage.rows == []

    async def profile_for(role):
        return job.profile

    monkeypatch.setattr(
        "ase.application.reports.production_version.build_report_assessment", assess
    )
    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=gateway,
        usage=usage,
    )
    version = await producer.produce(job, profile_for, before_persist)
    assert observed == [version.body]
    assert version.assessment == build_report_assessment(
        version.body,
        version.evidence,
        version.findings,
    )
    assert version.assessment is not None
    assert version.assessment.method_version in version.markdown


async def test_failed_generation_still_has_an_honest_frozen_assessment(
    container: Container,
    user: User,
) -> None:
    job = production_job(user, container.cipher)

    async def no_profile(role):
        return None

    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=ScriptedGateway("{}", "{}", "{}"),
        usage=RecordingUsage(),
    )
    version = await producer.produce(job, no_profile)
    assert version.status is ReportStatus.FAILED
    assert version.assessment is not None
    assert version.assessment.tallies.judgements == 0
    assert version.assessment.validation_errors > 0
    assert "Judgements: 0" in version.markdown
