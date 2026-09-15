"""Frozen ReportVersion metadata boundary, without live grading or registry reads."""

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from ase.domain.evidence import EvidenceItem
from ase.domain.reports import ReportBody
from ase.domain.source_assessment_bindings import assert_source_assessment_matches
from ase.domain.source_assessment_records import (
    source_assessment_capture_from_dict,
    source_assessment_capture_to_dict,
)
from ase.domain.source_assessment_report import (
    SourceAssessmentCapture,
    SourceAssessmentSnapshotError,
)


def _validate_capture(
    capture: SourceAssessmentCapture,
    *,
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
) -> None:
    if capture.report_version_id != report_version_id:
        raise SourceAssessmentSnapshotError("Source-assessment receipt belongs to another version.")
    if capture.projection is not None:
        assert_source_assessment_matches(
            capture.projection, report_version_id=report_version_id, body=body, evidence=evidence
        )


def source_assessment_from_analysis(
    data: Mapping[str, Any] | None,
    *,
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
) -> SourceAssessmentCapture | None:
    """Legacy absence remains absent; present malformed or stale data is refused."""
    if data is None or "source_assessment" not in data:
        return None
    capture = source_assessment_capture_from_dict(data["source_assessment"])
    _validate_capture(capture, report_version_id=report_version_id, body=body, evidence=evidence)
    return capture


def source_assessment_analysis_fields(
    capture: SourceAssessmentCapture | None,
    *,
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
) -> dict[str, Any]:
    """Validate the same binding on writes and reads, without inventing legacy data."""
    if capture is None:
        return {}
    data = source_assessment_capture_to_dict(capture)
    _validate_capture(capture, report_version_id=report_version_id, body=body, evidence=evidence)
    return {"source_assessment": data}
