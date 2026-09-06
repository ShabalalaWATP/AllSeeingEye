"""Persisted reports: the record, its versions, and JSON conversion of the body and findings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from ase.domain.advocacy import DevilsAdvocacy, advocacy_from_dict, advocacy_to_dict
from ase.domain.direction import Direction, direction_from_dict, direction_to_dict
from ase.domain.doctrine import Confidence
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.evidence_matrix import ReportAssessment
from ase.domain.report_assessment_records import assessment_to_dict
from ase.domain.reports import ReportBody, ReportHeader, ReportStatus, parse_body
from ase.domain.validation import Finding, Severity


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


def analysis_to_dict(version: ReportVersion) -> dict[str, Any] | None:
    """Optional frozen version metadata, without inventing an assessment for legacy records."""
    if (
        version.direction is None
        and version.advocacy is None
        and version.period_from is None
        and version.assessment is None
    ):
        return None
    return {
        "direction": direction_to_dict(version.direction) if version.direction else None,
        "devils_advocacy": advocacy_to_dict(version.advocacy) if version.advocacy else None,
        **({"assessment": assessment_to_dict(version.assessment)} if version.assessment else {}),
        "period": {
            "from": version.period_from.isoformat() if version.period_from else None,
            "to": version.period_to.isoformat() if version.period_to else None,
            "cutoff": version.data_cutoff.isoformat() if version.data_cutoff else None,
        },
    }


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
    )


def evidence_to_list(items: tuple[EvidenceItem, ...]) -> list[dict[str, Any]]:
    rows = []
    for item in items:
        data = asdict(item)
        data["published_at"] = item.published_at.isoformat()
        data["captured_at"] = item.captured_at.isoformat()
        data["observed_at"] = item.observed_at.isoformat() if item.observed_at else None
        data["flags"] = list(item.flags)
        rows.append(data)
    return rows


def evidence_from_list(rows: list[Mapping[str, Any]]) -> tuple[EvidenceItem, ...]:
    return tuple(
        EvidenceItem(
            label=str(row["label"]),
            event_id=str(row["event_id"]),
            source_id=str(row["source_id"]),
            source_name=str(row["source_name"]),
            independence_key=str(row["independence_key"]),
            category=str(row["category"]),
            title=str(row["title"]),
            summary=row.get("summary"),
            url=row.get("url"),
            published_at=datetime.fromisoformat(str(row["published_at"])),
            captured_at=datetime.fromisoformat(str(row["captured_at"])),
            grade=str(row["grade"]),
            reliability=str(row["reliability"]),
            credibility=int(row["credibility"]),
            grade_rationale=str(row.get("grade_rationale", "")),
            lon=row.get("lon"),
            lat=row.get("lat"),
            country_iso=row.get("country_iso"),
            content_hash=str(row.get("content_hash", "")),
            instrument=bool(row.get("instrument", False)),
            flags=tuple(str(flag) for flag in row.get("flags", [])),
            archive_url=row.get("archive_url"),
            title_en=row.get("title_en"),
            language=row.get("language"),
            geo_confidence=row.get("geo_confidence"),
            observed_at=(
                datetime.fromisoformat(str(row["observed_at"])) if row.get("observed_at") else None
            ),
            story_id=row.get("story_id"),
        )
        for row in rows
    )
