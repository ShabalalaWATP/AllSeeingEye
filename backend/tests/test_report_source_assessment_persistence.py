"""Frozen A01 metadata survives report storage without regrading shared evidence."""

import copy
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.adapters.persistence.models import ReportVersionRow
from ase.domain.report_records import analysis_to_dict
from ase.domain.source_assessment_capture import source_assessment_from_analysis
from ase.domain.source_assessment_records import source_assessment_capture_to_dict
from ase.domain.source_assessment_report import (
    SourceAssessmentCapture,
    SourceAssessmentSnapshotError,
)
from report_documents_helpers import document_records
from source_assessment_helpers import NOW
from source_projection_helpers import BODY, EVIDENCE, VERSION, projection


def frozen_records():
    record, version = document_records()
    capture = SourceAssessmentCapture(VERSION, NOW, "captured", projection())
    return record, replace(
        version, id=VERSION, body=BODY, evidence=EVIDENCE, source_assessment=capture
    )


async def test_reviewed_projection_round_trips_and_legacy_version_stays_absent(container):
    record, version = frozen_records()
    legacy = replace(version, id=uuid4(), source_assessment=None)
    latest = replace(version, number=2)
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        await repository.add(record, legacy)
        await repository.add_version(replace(record, latest_version=2), latest)
        await session.commit()
    # A later default projection has F/6; loading history must not consult it.
    assert projection(rated=False) != latest.source_assessment.projection
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        saved = await repository.get_version(record.id, 2)
        old = await repository.get_version(record.id, 1)
        row = await session.get(ReportVersionRow, legacy.id)
    assert saved.source_assessment == latest.source_assessment
    assert saved.evidence == EVIDENCE
    assert saved.body == BODY
    assert old.source_assessment is None
    assert old.evidence == EVIDENCE
    assert "source_assessment" not in row.analysis


async def test_late_archive_update_keeps_exact_assessment_readable(container):
    record, version = frozen_records()
    before = analysis_to_dict(version)["source_assessment"]
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        await repository.add(record, version)
        await repository.set_archives(
            version.id, {"E1": "https://example.org/archive"}, "Updated archive link"
        )
        await session.commit()
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(record.id, 1)
        row = await session.get(ReportVersionRow, version.id)
    assert saved.evidence[0].archive_url == "https://example.org/archive"
    assert saved.source_assessment == version.source_assessment
    assert row.analysis["source_assessment"] == before
    assert analysis_to_dict(saved)["source_assessment"] == before


@pytest.mark.parametrize("change", ["text", "evidence", "version"])
def test_write_rejects_stale_capture_binding(change):
    _, version = frozen_records()
    if change == "text":
        version.body = replace(
            BODY, key_judgements=(replace(BODY.key_judgements[0], statement="Changed."),)
        )
    elif change == "evidence":
        version.evidence = (replace(EVIDENCE[0], summary="Changed captured text."),)
    else:
        version.id = uuid4()
    with pytest.raises(SourceAssessmentSnapshotError):
        analysis_to_dict(version)


@pytest.mark.parametrize("change", ["text", "evidence", "null", "version", "schema", "status"])
async def test_read_refuses_present_invalid_metadata_instead_of_reconstructing(container, change):
    record, version = frozen_records()
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        await repository.add(record, version)
        row = await session.get(ReportVersionRow, version.id)
        if change == "text":
            body = copy.deepcopy(row.body)
            body["key_judgements"][0]["statement"] = "Changed saved judgement."
            row.body = body
        elif change == "evidence":
            evidence = copy.deepcopy(row.evidence)
            evidence[0]["grade"] = "F6"
            row.evidence = evidence
        else:
            analysis = copy.deepcopy(row.analysis)
            if change == "null":
                analysis["source_assessment"] = None
            elif change == "version":
                analysis["source_assessment"]["report_version_id"] = str(uuid4())
            elif change == "schema":
                analysis["source_assessment"]["schema_version"] = 2
            else:
                analysis["source_assessment"]["status"] = "unavailable"
            row.analysis = analysis
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(SourceAssessmentSnapshotError):
            await container.repositories(session).reports.get_version(record.id, 1)


@pytest.mark.parametrize("data", [None, {}, {"assessment": None}])
def test_legacy_analysis_never_invents_an_assessment(data):
    assert (
        source_assessment_from_analysis(
            data, report_version_id=VERSION, body=BODY, evidence=EVIDENCE
        )
        is None
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": True},
        {"schema_version": 2},
        {"status": "complete"},
        {"reason": "Unexpected"},
        {"projection": None},
        {"report_version_id": uuid4()},
    ],
)
def test_capture_receipt_requires_exact_projection_and_supported_version(changes):
    _, version = frozen_records()
    with pytest.raises(ValueError):
        replace(version.source_assessment, **changes)


def test_unavailable_receipt_is_explicit_and_json_detached():
    capture = SourceAssessmentCapture(VERSION, NOW, "unavailable", reason="Unresolved citations.")
    data = {"source_assessment": source_assessment_capture_to_dict(capture)}
    restored = source_assessment_from_analysis(
        data, report_version_id=VERSION, body=BODY, evidence=EVIDENCE
    )
    data["source_assessment"]["reason"] = "Changed detached JSON."
    assert restored == capture
    with pytest.raises(ValueError):
        replace(capture, reason=None)
    with pytest.raises(ValueError):
        replace(capture, projection=projection())
