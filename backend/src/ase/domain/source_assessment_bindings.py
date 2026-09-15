"""Exact report/evidence identity checks shared by creation and persistence."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_records import evidence_to_list
from ase.domain.reports import ReportBody
from ase.domain.source_assessment_report import (
    MAX_REPORT_SOURCE_CLAIMS,
    MAX_REPORT_SOURCE_EVIDENCE,
    MAX_REPORT_SOURCE_PAIRS,
    ReportSourceAssessment,
    ReportSourceClaim,
    ReportSourceEvidence,
    ReportSourceUse,
    SourceAssessmentSnapshotError,
    SourceUseRole,
    capture_identity,
    claim_identity,
)


@dataclass(frozen=True, slots=True)
class SourceAssessmentTargets:
    report_version_id: UUID
    evidence: tuple[ReportSourceEvidence, ...]
    claims: tuple[ReportSourceClaim, ...]


def _digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def prepare_source_assessment_targets(
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    *,
    subjects: Mapping[str, str],
) -> SourceAssessmentTargets:
    """Expose exact capture/claim IDs before querying the authorised review store.

    Subjects are explicit judgement-to-subject keys. Country, feed category and
    model prose do not supply an inferred expertise scope. Capture hashes bind
    the frozen evidence record, including original and translated text. The late
    archive URL is presentation metadata and is deliberately excluded.
    """
    if (
        not isinstance(report_version_id, UUID)
        or not isinstance(body, ReportBody)
        or len(evidence) > MAX_REPORT_SOURCE_EVIDENCE
        or len(body.key_judgements) > MAX_REPORT_SOURCE_CLAIMS
        or any(not isinstance(item, EvidenceItem) for item in evidence)
    ):
        raise ValueError("Source projection requires a bounded report and frozen evidence.")
    judgement_ids = {row.id for row in body.key_judgements}
    if len(judgement_ids) != len(body.key_judgements) or set(subjects) != judgement_ids:
        raise ValueError("Each final judgement requires one explicit subject scope.")
    if len({item.label for item in evidence}) != len(evidence) or len(
        {item.event_id for item in evidence}
    ) != len(evidence):
        raise ValueError("Frozen evidence labels and event captures must be unique.")
    manifest = []
    for item in sorted(evidence, key=lambda item: item.label):
        capture = evidence_to_list((item,))[0]
        capture.pop("archive_url", None)
        digest = _digest(capture)
        manifest.append(
            ReportSourceEvidence(
                capture_identity(report_version_id, digest),
                item.label,
                item.event_id,
                item.source_id,
                digest,
                item.independence_key.strip() or None,
            )
        )
    labels = {row.label: row for row in manifest}
    claims = []
    for judgement in sorted(body.key_judgements, key=lambda row: row.id):
        roles: dict[str, set[SourceUseRole]] = {}
        relations: tuple[tuple[SourceUseRole, tuple[str, ...]], ...] = (
            ("supporting", judgement.supporting_evidence),
            ("contradicting", judgement.contradicting_evidence),
        )
        for role, cited in relations:
            for label in cited:
                if label not in labels:
                    raise ValueError(
                        "A claim cannot cite evidence absent from the frozen manifest."
                    )
                roles.setdefault(label, set()).add(role)
        digest = _digest(
            {
                "statement": judgement.statement,
                "probability": judgement.probability.value,
                "assumptions": judgement.assumptions,
            }
        )
        claims.append(
            ReportSourceClaim(
                claim_identity(report_version_id, judgement.id, digest),
                judgement.id,
                subjects[judgement.id],
                digest,
                tuple(
                    sorted(
                        (
                            ReportSourceUse(labels[label].capture_id, tuple(sorted(values)))
                            for label, values in roles.items()
                        ),
                        key=lambda row: row.capture_id,
                    )
                ),
            )
        )
    if sum(len(claim.uses) for claim in claims) > MAX_REPORT_SOURCE_PAIRS:
        raise ValueError("The source projection exceeds its captured-claim allowance.")
    return SourceAssessmentTargets(report_version_id, tuple(manifest), tuple(claims))


def assert_source_assessment_matches(
    report: ReportSourceAssessment,
    *,
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
) -> None:
    """Refuse changed saved bindings without consulting current source ratings."""
    try:
        expected = prepare_source_assessment_targets(
            report_version_id,
            body,
            evidence,
            subjects={row.judgement_id: row.subject for row in report.claims},
        )
        if (
            report.report_version_id != report_version_id
            or report.evidence != expected.evidence
            or report.claims != expected.claims
        ):
            raise ValueError("The frozen source projection does not match this report version.")
    except (ValueError, TypeError, KeyError, AttributeError):
        raise SourceAssessmentSnapshotError(
            "Source assessment does not match the frozen report."
        ) from None
