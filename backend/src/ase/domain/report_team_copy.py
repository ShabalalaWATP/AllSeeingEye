"""A team copy of one finished personal report version, made without another model run.

The copy keeps the selected version's analytical content: body and figures, findings,
frozen evidence with its content hashes, quality, assessment values and the exact
authored questions. It receives new report and version identities in the team's
scope. References that would reach private material in the personal scope (the
Research Brief, the claim ledger, retained original passages, plans, parent reports
and private-input metadata) are omitted and listed, never carried across.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from ase.domain.evidence import EvidenceItem
from ase.domain.report_assessment_records import assessment_to_dict
from ase.domain.report_records import (
    ReportRecord,
    ReportVersion,
    body_to_dict,
    evidence_to_list,
    findings_to_list,
    quality_to_dict,
)
from ase.domain.research_records import ResearchReceipt
from ase.domain.source_assessment_rebinding import rebind_source_assessment

# Evidence extracted from material the operator uploaded, not public reporting.
PRIVATE_INPUT_SOURCES = frozenset({"research_import", "research_media"})

# Analytical scope carried to the copy. Anything else, including keys added later,
# stays with the personal original until it is reviewed for team visibility.
COPIED_SCOPE_KEYS = frozenset(
    {
        "origin",
        "regions",
        "research_time_basis",
        "research_since",
        "research_until",
        "report_language",
        "report_style",
        "country",
        "countries",
        "categories",
        "question",
        "window_hours",
        "devils_advocacy",
        "hazard",
        "conflict",
        "research_area",
        "disclose_area_to_provider",
        "research_candidate_hypotheses",
        "research_planned_tasks",
        "research_mode",
        "research_web_search",
        "research_languages",
        "research_source_ids",
        "research_query_variants",
        "research_terms",
        "research_focus",
        "research_subject",
    }
)


class TeamCopyOmission(StrEnum):
    RESEARCH_BRIEF = "research_brief"
    CLAIM_GENERATION = "claim_generation"
    ORIGINAL_PASSAGES = "original_passages"
    SOURCE_ASSESSMENT = "source_assessment"
    SCOPE_REFERENCES = "scope_references"


@dataclass(frozen=True, slots=True)
class PrivateInputDisclosure:
    label: str
    title: str
    source_id: str


@dataclass(frozen=True, slots=True)
class TeamCopyPlan:
    private_inputs: tuple[PrivateInputDisclosure, ...]
    omissions: tuple[TeamCopyOmission, ...]
    omitted_scope_keys: tuple[str, ...]
    content_sha256: str


@dataclass(frozen=True, slots=True)
class LinkedArtefacts:
    """Records attached to the personal version that are never copied."""

    claims: int = 0
    original_files: int = 0
    original_passages: int = 0
    reviewed_snapshots: int = 0
    map_views: int = 0


@dataclass(frozen=True, slots=True)
class ReportTeamCopy:
    """Provenance of one team copy: who copied which version, when, and what was left out."""

    id: UUID
    report_id: UUID
    team_id: UUID
    source_report_id: UUID
    source_version_id: UUID
    source_version_number: int
    copied_by: UUID
    copied_at: datetime
    content_sha256: str
    disclosed_labels: tuple[str, ...]
    omissions: tuple[TeamCopyOmission, ...]


def is_private_input(item: EvidenceItem) -> bool:
    return item.source_id in PRIVATE_INPUT_SOURCES


def report_content_sha256(version: ReportVersion) -> str:
    """Digest of the promised content, independent of report and version identities."""
    content: dict[str, Any] = {
        "body": body_to_dict(version.body),
        "findings": findings_to_list(version.findings),
        "evidence": evidence_to_list(version.evidence),
        "quality": quality_to_dict(version.quality),
        "assessment": assessment_to_dict(version.assessment) if version.assessment else None,
        "requirements": [asdict(row) for row in version.canonical_requirements],
    }
    encoded = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _passages_omitted(research: ResearchReceipt | None) -> bool:
    return research is not None and any(
        row.passage_ref is not None for row in research.original_followup
    )


def _research_without_passages(research: ResearchReceipt | None) -> ResearchReceipt | None:
    if research is None or not _passages_omitted(research):
        return research
    return replace(
        research,
        original_followup=tuple(
            replace(
                row,
                status="unavailable",
                reason="omitted_from_team_copy",
                passage_ref=None,
                passage_id=None,
                document_version_id=None,
            )
            if row.passage_ref is not None
            else row
            for row in research.original_followup
        ),
    )


def _rebound(version: ReportVersion, version_id: UUID) -> tuple[ReportVersion, bool]:
    copied = replace(
        version,
        id=version_id,
        brief_id=None,
        brief_revision=None,
        claim_generation=None,
        research=_research_without_passages(version.research),
        source_assessment=None,
    )
    if version.source_assessment is None:
        return copied, True
    capture, preserved = rebind_source_assessment(
        version.source_assessment,
        report_version_id=version_id,
        body=version.body,
        evidence=version.evidence,
    )
    return replace(copied, source_assessment=capture), preserved


def plan_team_copy(record: ReportRecord, version: ReportVersion) -> TeamCopyPlan:
    """What a copy discloses to the team and what it leaves with the personal original."""
    omissions: list[TeamCopyOmission] = []
    if version.brief_id is not None:
        omissions.append(TeamCopyOmission.RESEARCH_BRIEF)
    if version.claim_generation is not None:
        omissions.append(TeamCopyOmission.CLAIM_GENERATION)
    if _passages_omitted(version.research):
        omissions.append(TeamCopyOmission.ORIGINAL_PASSAGES)
    if version.source_assessment is not None and not _rebound(version, version.id)[1]:
        omissions.append(TeamCopyOmission.SOURCE_ASSESSMENT)
    omitted_keys = tuple(sorted(key for key in record.scope if key not in COPIED_SCOPE_KEYS))
    if omitted_keys:
        omissions.append(TeamCopyOmission.SCOPE_REFERENCES)
    return TeamCopyPlan(
        tuple(
            PrivateInputDisclosure(item.label, item.title, item.source_id)
            for item in version.evidence
            if is_private_input(item)
        ),
        tuple(omissions),
        omitted_keys,
        report_content_sha256(version),
    )


def copy_for_team(
    record: ReportRecord,
    version: ReportVersion,
    *,
    report_id: UUID,
    version_id: UUID,
    team_id: UUID,
    copied_by: UUID,
    now: datetime,
) -> tuple[ReportRecord, ReportVersion]:
    """A new team report holding the selected version as its first and only version."""
    copied, _ = _rebound(version, version_id)
    copied = replace(copied, report_id=report_id, number=1)
    team_record = ReportRecord(
        id=report_id,
        template=record.template,
        title=record.title,
        scope={key: value for key, value in record.scope.items() if key in COPIED_SCOPE_KEYS},
        period_from=version.period_from or record.period_from,
        period_to=version.period_to or record.period_to,
        data_cutoff=version.data_cutoff or record.data_cutoff,
        status=version.status,
        created_by=copied_by,
        created_at=now,
        latest_version=1,
        team_id=team_id,
    )
    return team_record, copied
