"""JSONL labelled set of human citation verdicts bound to one exact saved report version.

Each row repeats the frozen judgement text and the cited excerpt so the set can be read
without the database. `binding_sha256` covers the exact version, judgement, citation and
excerpt fields, so a reader can reject rows whose bindings were edited or mixed up.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ase.domain.citation_checks import CitationCheck, ReportCitationChecks
from ase.domain.citation_verdicts import (
    HUMAN_OPINION_NOTE,
    VERDICT_DATASET,
    CitationAnchor,
    CitationVerdict,
    current_verdicts,
)
from ase.domain.report_records import ReportVersion

BINDING_FIELDS = (
    "report_id",
    "report_version_id",
    "version_number",
    "judgement_id",
    "judgement_statement",
    "label",
    "relation",
    "source_id",
    "event_id",
    "source_content_hash",
    "excerpt",
)


def binding_digest(row: Mapping[str, Any]) -> str:
    bound = {name: row.get(name) for name in BINDING_FIELDS}
    payload = json.dumps(bound, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _check(checks: ReportCitationChecks | None, anchor: CitationAnchor) -> CitationCheck | None:
    if checks is None:
        return None
    for judgement in checks.judgements:
        if judgement.judgement_id != anchor.judgement_id:
            continue
        for citation in judgement.citations:
            if citation.label == anchor.label and citation.relation == anchor.relation:
                return citation
    return None


def verdict_rows(
    version: ReportVersion, verdicts: Sequence[CitationVerdict]
) -> list[dict[str, Any]]:
    statements = {row.id: row.statement for row in version.body.key_judgements}
    evidence = {item.label: item for item in version.evidence}
    current = {row.id for row in current_verdicts(verdicts)}
    rows = []
    for verdict in sorted(verdicts, key=lambda item: (item.recorded_at, str(item.id))):
        if verdict.report_version_id != version.id:
            raise ValueError("A verdict export covers one exact report version.")
        anchor = verdict.anchor
        check = _check(version.citation_checks, anchor)
        item = evidence.get(anchor.label)
        excerpt = check.excerpt if check is not None else None
        row: dict[str, Any] = {
            "record": "verdict",
            "dataset": VERDICT_DATASET,
            "verdict_id": str(verdict.id),
            "report_id": str(version.report_id),
            "report_version_id": str(version.id),
            "version_number": version.number,
            "judgement_id": anchor.judgement_id,
            "judgement_statement": statements.get(anchor.judgement_id),
            "label": anchor.label,
            "relation": anchor.relation,
            "source_id": item.source_id if item is not None else None,
            "event_id": item.event_id if item is not None else None,
            "source_content_hash": check.source_content_hash if check is not None else None,
            "excerpt": (
                {
                    "field": excerpt.field,
                    "start": excerpt.start,
                    "end": excerpt.end,
                    "text": excerpt.text,
                    "sha256": excerpt.sha256,
                }
                if excerpt is not None
                else None
            ),
            "citation_check_status": check.status.value if check is not None else None,
            "citation_check_method": (
                version.citation_checks.method_version
                if version.citation_checks is not None
                else None
            ),
            "verdict": verdict.verdict.value,
            "note": verdict.note,
            "reviewer_id": str(verdict.reviewer_id),
            "team_scoped": verdict.team_id is not None,
            "recorded_at": verdict.recorded_at.isoformat(),
            "current": verdict.id in current,
        }
        row["binding_sha256"] = binding_digest(row)
        rows.append(row)
    return rows


def encode_verdict_export(
    version: ReportVersion, verdicts: Sequence[CitationVerdict], generated_at: datetime
) -> bytes:
    rows = verdict_rows(version, verdicts)
    header = {
        "record": "header",
        "dataset": VERDICT_DATASET,
        "origin": "saved application report",
        "report_id": str(version.report_id),
        "report_version_id": str(version.id),
        "version_number": version.number,
        "generated_at": generated_at.isoformat(),
        "verdicts": len(rows),
        "notice": HUMAN_OPINION_NOTE,
    }
    lines = [json.dumps(row, sort_keys=True, ensure_ascii=False) for row in (header, *rows)]
    return ("\n".join(lines) + "\n").encode("utf-8")
