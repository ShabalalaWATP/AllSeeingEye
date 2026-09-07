"""Validate model-proposed assertions against exact frozen original evidence.

This parser neither verifies atomicity nor changes grades. Model proposals remain
unreviewed; the caller must retain model provenance and enforce its call budget.
"""

from dataclasses import dataclass

from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimKind,
    ClaimRelation,
    freeze_claim_citations,
)
from ase.domain.evidence import injection_flags
from ase.domain.report_records import ReportVersion

MAX_PROPOSALS = 20
MAX_PROPOSAL_CITATIONS = 5


@dataclass(frozen=True, slots=True)
class ClaimProposal:
    statement: str
    kind: ClaimKind
    citations: tuple[ClaimCitationInput, ...]
    unresolved_conflicts: tuple[str, ...]


def _text(value: object, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Invalid proposal text")
    value.encode("utf-8")
    if injection_flags(value) or any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError("Unsafe proposal text")
    return value


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Unexpected proposal fields")
    return value


def parse_claim_proposals(payload: object, version: ReportVersion) -> tuple[ClaimProposal, ...]:
    value = _object(payload, {"claims"})
    rows = value["claims"]
    if not isinstance(rows, list) or len(rows) > MAX_PROPOSALS:
        raise ValueError("Too many claim proposals")
    evidence = {item.label: item for item in version.evidence}
    if len(evidence) != len(version.evidence):
        raise ValueError("Ambiguous evidence labels")
    proposals = []
    statements = set()
    for raw in rows:
        row = _object(raw, {"statement", "kind", "citations", "unresolved_conflicts"})
        statement = _text(row["statement"], 1200)
        if statement in statements:
            raise ValueError("Duplicate claim proposal")
        statements.add(statement)
        kind = ClaimKind(_text(row["kind"], 32))
        citations = row["citations"]
        conflicts = row["unresolved_conflicts"]
        if not isinstance(citations, list) or not 1 <= len(citations) <= MAX_PROPOSAL_CITATIONS:
            raise ValueError("Invalid proposal citation count")
        if not isinstance(conflicts, list) or len(conflicts) > 20:
            raise ValueError("Invalid proposal conflicts")
        inputs = []
        for raw_citation in citations:
            citation = _object(raw_citation, {"label", "relation", "field", "text"})
            label, field = _text(citation["label"], 32), _text(citation["field"], 16)
            item = evidence.get(label)
            if item is None or field not in ("title", "summary"):
                raise ValueError("Proposal must cite original frozen evidence")
            text = _text(citation["text"], 1200)
            source = item.title if field == "title" else item.summary or ""
            start = source.find(text)
            if start < 0 or source.find(text, start + 1) >= 0:
                raise ValueError("Proposal excerpt is missing or has ambiguous occurrences")
            inputs.append(
                ClaimCitationInput(
                    label,
                    ClaimRelation(_text(citation["relation"], 16)),
                    field,
                    start,
                    start + len(text),
                    text,
                )
            )
        frozen_inputs = tuple(inputs)
        freeze_claim_citations(version, frozen_inputs)
        proposals.append(
            ClaimProposal(
                statement,
                kind,
                frozen_inputs,
                tuple(_text(conflict, 1200) for conflict in conflicts),
            )
        )
    return tuple(proposals)
