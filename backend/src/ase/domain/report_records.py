"""Persisted reports: the record, its versions, and JSON conversion of the body and findings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from ase.domain.advocacy import DevilsAdvocacy, advocacy_from_dict, advocacy_to_dict
from ase.domain.challenge import ReportChallenge
from ase.domain.challenge_records import challenge_to_dict
from ase.domain.citation_check_records import citation_checks_to_dict
from ase.domain.citation_checks import ReportCitationChecks
from ase.domain.claim_generation import ClaimGenerationReceipt, claim_generation_to_dict
from ase.domain.direction import Direction, direction_from_dict, direction_to_dict
from ase.domain.doctrine import Confidence
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.evidence_coverage import coverage_from_dict, coverage_to_dict
from ase.domain.evidence_matrix import ReportAssessment
from ase.domain.evidence_records import evidence_from_list, evidence_to_list
from ase.domain.model_routing import ModelRoutingRecord
from ase.domain.model_routing_records import routing_to_dict
from ase.domain.report_assessment_records import assessment_to_dict
from ase.domain.reports import ReportBody, ReportHeader, ReportStatus, parse_body
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.research_context import ResearchContext
from ase.domain.research_context_records import context_to_dict
from ase.domain.research_records import ResearchReceipt, research_to_dict
from ase.domain.source_assessment_capture import source_assessment_analysis_fields
from ase.domain.source_assessment_report import SourceAssessmentCapture
from ase.domain.validation import Finding, Severity

__all__ = [
    "ReportRecord",
    "ReportVersion",
    "analysis_from_dict",
    "analysis_to_dict",
    "body_from_dict",
    "body_to_dict",
    "brief_reference_from_analysis",
    "document_schema_version_from_analysis",
    "evidence_from_list",
    "evidence_to_list",
    "findings_from_list",
    "findings_to_list",
    "quality_from_dict",
    "quality_to_dict",
    "requirements_from_analysis",
]


@dataclass(slots=True)
class ReportRecord:
    id: UUID
    template: str
    title: str
    scope: Mapping[str, Any]
    period_from: datetime
    period_to: datetime
    data_cutoff: datetime
    status: ReportStatus
    created_by: UUID
    created_at: datetime
    latest_version: int
    team_id: UUID | None = None

    @property
    def header(self) -> ReportHeader:
        return ReportHeader(
            template=self.template,
            title=self.title,
            scope=self.scope,
            period_from=self.period_from,
            period_to=self.period_to,
            data_cutoff=self.data_cutoff,
        )


@dataclass(slots=True)
class ReportVersion:
    id: UUID
    report_id: UUID
    number: int
    status: ReportStatus
    body: ReportBody
    findings: tuple[Finding, ...]
    evidence: tuple[EvidenceItem, ...]
    quality: QualityOfInformation
    markdown: str
    profile_id: UUID | None
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: float
    attempts: int
    created_at: datetime
    direction: Direction | None = None
    advocacy: DevilsAdvocacy | None = None
    period_from: datetime | None = None
    period_to: datetime | None = None
    data_cutoff: datetime | None = None
    assessment: ReportAssessment | None = None
    research: ResearchReceipt | None = None
    citation_checks: ReportCitationChecks | None = None
    research_context: ResearchContext | None = None
    challenge: ReportChallenge | None = None
    model_routing: ModelRoutingRecord | None = None
    claim_generation: ClaimGenerationReceipt | None = None
    canonical_requirements: tuple[IntelligenceRequirement, ...] = ()
    brief_id: UUID | None = None
    brief_revision: int | None = None
    document_schema_version: int = 1
    source_assessment: SourceAssessmentCapture | None = None


def analysis_to_dict(version: ReportVersion) -> dict[str, Any] | None:
    """Optional frozen version metadata, without inventing an assessment for legacy records."""
    if (version.brief_id is None) != (version.brief_revision is None):
        raise ValueError("A report version must pin both Research Brief identifiers")
    if version.brief_revision is not None and (
        not isinstance(version.brief_id, UUID)
        or type(version.brief_revision) is not int
        or version.brief_revision < 1
    ):
        raise ValueError("Invalid frozen Research Brief reference")
    if type(version.document_schema_version) is not int or version.document_schema_version not in (
        1,
        2,
    ):
        raise ValueError("Unsupported frozen document projection version")
    if (
        version.direction is None
        and version.advocacy is None
        and version.period_from is None
        and version.assessment is None
        and version.research is None
        and version.citation_checks is None
        and version.research_context is None
        and version.challenge is None
        and version.model_routing is None
        and version.claim_generation is None
        and version.source_assessment is None
        and not version.canonical_requirements
        and version.brief_id is None
        and version.document_schema_version == 1
    ):
        return None
    return {
        **source_assessment_analysis_fields(
            version.source_assessment,
            report_version_id=version.id,
            body=version.body,
            evidence=version.evidence,
        ),
        **(
            {"document_schema_version": version.document_schema_version}
            if version.document_schema_version != 1
            else {}
        ),
        **(
            {"brief_reference": {"id": str(version.brief_id), "revision": version.brief_revision}}
            if version.brief_id is not None
            else {}
        ),
        **(
            {"canonical_requirements": [asdict(row) for row in version.canonical_requirements]}
            if version.canonical_requirements
            else {}
        ),
        **(
            {"claim_generation": claim_generation_to_dict(version.claim_generation)}
            if version.claim_generation is not None
            else {}
        ),
        "model_routing": routing_to_dict(version.model_routing),
        **({"challenge": challenge_to_dict(version.challenge)} if version.challenge else {}),
        "direction": direction_to_dict(version.direction) if version.direction else None,
        "devils_advocacy": advocacy_to_dict(version.advocacy) if version.advocacy else None,
        **({"assessment": assessment_to_dict(version.assessment)} if version.assessment else {}),
        **({"research": research_to_dict(version.research)} if version.research else {}),
        **(
            {"research_context": context_to_dict(version.research_context)}
            if version.research_context is not None
            else {}
        ),
        **(
            {"citation_checks": citation_checks_to_dict(version.citation_checks)}
            if version.citation_checks
            else {}
        ),
        "period": {
            "from": version.period_from.isoformat() if version.period_from else None,
            "to": version.period_to.isoformat() if version.period_to else None,
            "cutoff": version.data_cutoff.isoformat() if version.data_cutoff else None,
        },
    }


def document_schema_version_from_analysis(data: Mapping[str, Any] | None) -> int:
    if not data or "document_schema_version" not in data:
        return 1
    version = data["document_schema_version"]
    if type(version) is not int or version != 2:
        raise ValueError("Unsupported frozen document projection version")
    return version


def requirements_from_analysis(
    data: Mapping[str, Any] | None,
) -> tuple[IntelligenceRequirement, ...]:
    """Restore exact authored questions from this version, independent of legacy Direction."""
    if not data or "canonical_requirements" not in data:
        return ()
    rows = data["canonical_requirements"]
    if not isinstance(rows, list) or len(rows) > 12:
        raise ValueError("Invalid saved canonical requirements")
    result: list[IntelligenceRequirement] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "question", "required", "priority"}:
            raise ValueError("Invalid saved canonical requirement")
        result.append(IntelligenceRequirement(**row))
    if len({row.id for row in result}) != len(result):
        raise ValueError("Duplicate saved canonical requirement")
    return tuple(result)


def brief_reference_from_analysis(
    data: Mapping[str, Any] | None,
) -> tuple[UUID | None, int | None]:
    if not data or "brief_reference" not in data:
        return None, None
    value = data["brief_reference"]
    if not isinstance(value, dict) or set(value) != {"id", "revision"}:
        raise ValueError("Invalid frozen Research Brief reference")
    if type(value["revision"]) is not int or value["revision"] < 1:
        raise ValueError("Invalid frozen Research Brief revision")
    try:
        return UUID(value["id"]), value["revision"]
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid frozen Research Brief identifier") from exc


def analysis_from_dict(
    data: Mapping[str, Any] | None,
) -> tuple[Direction | None, DevilsAdvocacy | None]:
    if not data:
        return None, None
    direction = data.get("direction")
    advocacy = data.get("devils_advocacy")
    return (
        direction_from_dict(direction) if direction else None,
        advocacy_from_dict(advocacy) if advocacy else None,
    )


def body_to_dict(body: ReportBody) -> dict[str, Any]:
    """JSON-safe dictionary; historic records use the tolerant inverse ``parse_body``."""
    return asdict(body)


def body_from_dict(data: Mapping[str, Any]) -> ReportBody:
    return parse_body(dict(data))


def findings_to_list(findings: tuple[Finding, ...]) -> list[dict[str, str]]:
    return [asdict(finding) for finding in findings]


def findings_from_list(items: list[Mapping[str, Any]]) -> tuple[Finding, ...]:
    return tuple(
        Finding(
            rule=str(item["rule"]),
            severity=Severity(str(item["severity"])),
            location=str(item["location"]),
            message=str(item["message"]),
        )
        for item in items
    )


def quality_to_dict(quality: QualityOfInformation) -> dict[str, Any]:
    data = asdict(quality)
    data["newest"] = quality.newest.isoformat() if quality.newest else None
    data["oldest"] = quality.oldest.isoformat() if quality.oldest else None
    data["confidence_ceiling"] = quality.confidence_ceiling.value
    # Absent on versions saved before coverage counts were recorded.
    data.pop("coverage")
    if quality.coverage is not None:
        data["coverage"] = coverage_to_dict(quality.coverage)
    return data


def quality_from_dict(data: Mapping[str, Any]) -> QualityOfInformation:
    return QualityOfInformation(
        items=int(data.get("items", 0)),
        by_grade={str(k): int(v) for k, v in dict(data.get("by_grade", {})).items()},
        independent_organisations=int(data.get("independent_organisations", 0)),
        instrument_share=float(data.get("instrument_share", 0.0)),
        newest=datetime.fromisoformat(data["newest"]) if data.get("newest") else None,
        oldest=datetime.fromisoformat(data["oldest"]) if data.get("oldest") else None,
        contradictions=(
            int(data["contradictions"]) if data.get("contradictions") is not None else None
        ),
        flagged=int(data.get("flagged", 0)),
        confidence_ceiling=Confidence(str(data.get("confidence_ceiling", "low"))),
        coverage=coverage_from_dict(data.get("coverage")),
    )
