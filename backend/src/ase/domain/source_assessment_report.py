"""Frozen claim-scoped source assessments for one exact report version.

This contract carries qualitative inputs, not a replacement confidence score.
It deliberately does not add grades to globally shared events or evidence items.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from ase.domain.origin_chains import ORIGIN_POLICY_VERSION, OriginAnalysis, analyse_origin_chains
from ase.domain.source_assessment import (
    ASSESSMENT_POLICY_VERSION,
    ScopedSourceAssessment,
    assessment_text,
    assessment_time,
)

REPORT_SOURCE_SCHEMA_VERSION = 1
MAX_REPORT_SOURCE_EVIDENCE = 100
MAX_REPORT_SOURCE_CLAIMS = 64
MAX_REPORT_SOURCE_PAIRS = 512
SourceUseRole = Literal["supporting", "contradicting"]


class SourceAssessmentSnapshotError(ValueError):
    """Safe failure for missing required or malformed saved source assessments."""


@dataclass(frozen=True, slots=True)
class SourceAssessmentCapture:
    """Versioned receipt distinguishes legacy absence from an unbindable draft.

    Unavailable receipts preserve reviewable paid work without pretending that
    its citations could be resolved. They do not confer an assessment or grade.
    """

    report_version_id: UUID
    frozen_at: datetime
    status: Literal["captured", "unavailable"]
    projection: "ReportSourceAssessment | None" = None
    reason: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.report_version_id, UUID):
            raise ValueError("A source-assessment receipt requires an exact report version.")
        assessment_time(self.frozen_at)
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("Unsupported source-assessment receipt version.")
        if self.status == "captured":
            if (
                not isinstance(self.projection, ReportSourceAssessment)
                or self.projection.report_version_id != self.report_version_id
                or self.projection.frozen_at != self.frozen_at
                or self.reason is not None
            ):
                raise ValueError("A captured receipt requires its exact frozen projection.")
        elif self.status == "unavailable":
            if self.projection is not None:
                raise ValueError("An unavailable receipt cannot contain an assessment.")
            assessment_text(self.reason)
        else:
            raise ValueError("Invalid source-assessment receipt status.")


def capture_identity(version_id: UUID, digest: str) -> str:
    return uuid5(NAMESPACE_URL, f"ase:source-capture:{version_id}:{digest}").hex


def claim_identity(version_id: UUID, judgement_id: str, digest: str) -> str:
    return uuid5(NAMESPACE_URL, f"ase:source-claim:{version_id}:{judgement_id}:{digest}").hex


def _digest(value: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("A report-source binding requires a complete content digest.")


@dataclass(frozen=True, slots=True)
class ReportSourceEvidence:
    capture_id: str
    label: str
    event_id: str
    source_id: str
    digest: str
    declared_organisation: str | None

    def __post_init__(self) -> None:
        for value in (self.capture_id, self.label, self.event_id, self.source_id):
            assessment_text(value, 120)
        _digest(self.digest)
        if self.declared_organisation is not None:
            assessment_text(self.declared_organisation, 200)


@dataclass(frozen=True, slots=True)
class ReportSourceUse:
    capture_id: str
    roles: tuple[SourceUseRole, ...]

    def __post_init__(self) -> None:
        assessment_text(self.capture_id, 120)
        if (
            type(self.roles) is not tuple
            or not self.roles
            or len(self.roles) > 2
            or self.roles != tuple(sorted(set(self.roles)))
            or any(role not in ("supporting", "contradicting") for role in self.roles)
        ):
            raise ValueError("Each captured claim requires unique, ordered evidence roles.")


@dataclass(frozen=True, slots=True)
class ReportSourceClaim:
    claim_id: str
    judgement_id: str
    subject: str
    digest: str
    uses: tuple[ReportSourceUse, ...]

    def __post_init__(self) -> None:
        for value in (self.claim_id, self.judgement_id, self.subject):
            assessment_text(value, 200)
        _digest(self.digest)
        if (
            type(self.uses) is not tuple
            or len(self.uses) > MAX_REPORT_SOURCE_EVIDENCE
            or any(not isinstance(row, ReportSourceUse) for row in self.uses)
            or len({row.capture_id for row in self.uses}) != len(self.uses)
        ):
            raise ValueError("Claim evidence uses require a bounded, unique immutable sequence.")


@dataclass(frozen=True, slots=True)
class ReportSourceAssessment:
    report_version_id: UUID
    frozen_at: datetime
    evidence: tuple[ReportSourceEvidence, ...]
    claims: tuple[ReportSourceClaim, ...]
    assessments: tuple[ScopedSourceAssessment, ...]
    origins: OriginAnalysis
    schema_version: int = REPORT_SOURCE_SCHEMA_VERSION
    policy_version: str = ASSESSMENT_POLICY_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.report_version_id, UUID):
            raise ValueError("Source assessments require an exact report version.")
        assessment_time(self.frozen_at)
        if (
            type(self.schema_version) is not int
            or self.schema_version != REPORT_SOURCE_SCHEMA_VERSION
        ):
            raise ValueError("Unsupported report-source schema version.")
        if self.policy_version != ASSESSMENT_POLICY_VERSION:
            raise ValueError("Unsupported report-source policy version.")
        for values, kind, maximum in (
            (self.evidence, ReportSourceEvidence, MAX_REPORT_SOURCE_EVIDENCE),
            (self.claims, ReportSourceClaim, MAX_REPORT_SOURCE_CLAIMS),
            (self.assessments, ScopedSourceAssessment, MAX_REPORT_SOURCE_PAIRS),
        ):
            if (
                type(values) is not tuple
                or len(values) > maximum
                or any(not isinstance(value, kind) for value in values)
            ):
                raise ValueError("Report-source records exceed their typed immutable bounds.")
        _validate_bindings(self)
        _validate_origins(self)


def _validate_bindings(report: ReportSourceAssessment) -> None:
    evidence = {row.capture_id: row for row in report.evidence}
    claims = {row.claim_id: row for row in report.claims}
    if (
        len(evidence) != len(report.evidence)
        or len({row.label for row in report.evidence}) != len(report.evidence)
        or len({row.event_id for row in report.evidence}) != len(report.evidence)
        or len(claims) != len(report.claims)
        or len({row.judgement_id for row in report.claims}) != len(report.claims)
        or any(
            row.capture_id != capture_identity(report.report_version_id, row.digest)
            for row in report.evidence
        )
        or any(
            row.claim_id != claim_identity(report.report_version_id, row.judgement_id, row.digest)
            for row in report.claims
        )
    ):
        raise ValueError("Source-assessment bindings must be unique and report-version specific.")
    expected = {(use.capture_id, row.claim_id) for row in report.claims for use in row.uses}
    actual = {(row.evidence_id, row.claim_id) for row in report.assessments}
    if (
        len(expected) > MAX_REPORT_SOURCE_PAIRS
        or actual != expected
        or len(actual) != len(report.assessments)
        or any(capture_id not in evidence for capture_id, _ in expected)
    ):
        raise ValueError("Every cited capture/claim pair requires exactly one frozen assessment.")
    for row in report.assessments:
        if (
            row.source_id != evidence[row.evidence_id].source_id
            or row.subject != claims[row.claim_id].subject
        ):
            raise ValueError("A source assessment cannot cross issuer or subject scope.")
        for revision in (row.source_revision, row.assertion_revision):
            if revision is not None and revision.review.recorded_at > report.frozen_at:
                raise ValueError("A frozen assessment cannot predate its applied rating.")


def _validate_origins(report: ReportSourceAssessment) -> None:
    origins = report.origins
    if not isinstance(origins, OriginAnalysis) or origins.policy_version != ORIGIN_POLICY_VERSION:
        raise ValueError("Unsupported report-source origin policy.")
    canonical = analyse_origin_chains(
        origins.nodes,
        [row.edge for row in origins.relationships],
        observations=origins.observations,
    )
    if origins != canonical:
        raise ValueError("Frozen origin groups and decisions must match their pinned policy.")
    evidence = {row.capture_id: row for row in report.evidence}
    claim_ids = {row.claim_id for row in report.claims}
    for node in origins.nodes:
        if (
            node.evidence_id not in evidence
            or node.claim_id not in claim_ids
            or node.source_id != evidence[node.evidence_id].source_id
            or node.organisation != evidence[node.evidence_id].declared_organisation
        ):
            raise ValueError(
                "Origin records must match captured evidence, claims and organisation."
            )
    pairs = {(node.evidence_id, node.claim_id) for node in origins.nodes}
    if any((row.evidence_id, row.claim_id) not in pairs for row in report.assessments):
        raise ValueError("Each assessed capture/claim pair requires explicit origin metadata.")
    if any(row.edge.recorded_at > report.frozen_at for row in origins.relationships):
        raise ValueError("A frozen assessment cannot predate its origin decisions.")
