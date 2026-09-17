"""The schema and parsing for one bounded entailment pass over the key judgements.

Literal citation checks find a missing or mismatched citation. They cannot find a
citation that is present, quoted correctly and simply does not support the claim. This
is the shape of the single model answer that looks for that, and nothing else: it
produces verdicts on cited extracts, never replacement text for the report.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

METHOD_VERSION = "ase-entailment-v1"
MAX_ROWS = 24
MAX_REASON_CHARS = 300

Verdict = Literal["supports", "partly_supports", "does_not_support"]
VERDICTS: tuple[Verdict, ...] = ("supports", "partly_supports", "does_not_support")

LIMITATIONS = (
    "A model read the frozen extract and the judgement. Its verdict is an opinion about "
    "wording, not a verification that the claim is true.",
    "Only the key judgements and their cited extracts were read, not the whole report or "
    "the full source article.",
)

ENTAILMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["assessments"],
    "properties": {
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["judgement_id", "label", "verdict", "reason"],
                "properties": {
                    "judgement_id": {"type": "string"},
                    "label": {"type": "string"},
                    "verdict": {"type": "string", "enum": list(VERDICTS)},
                    "reason": {"type": "string"},
                },
            },
        }
    },
}


class EntailmentParseError(ValueError):
    """The model's JSON does not fit the entailment schema; the message names the field."""


@dataclass(frozen=True, slots=True)
class CitationEntailment:
    judgement_id: str
    label: str
    verdict: Verdict
    reason: str


def parse_entailment(
    data: Any, allowed: frozenset[tuple[str, str]]
) -> tuple[CitationEntailment, ...]:
    """Keep only verdicts on pairs that were actually asked about, bounding every field."""
    if not isinstance(data, dict):
        raise EntailmentParseError("the entailment answer must be a JSON object")
    rows = data.get("assessments")
    if not isinstance(rows, list):
        raise EntailmentParseError("assessments must be a list")
    kept: list[CitationEntailment] = []
    seen: set[tuple[str, str]] = set()
    for row in rows[:MAX_ROWS]:
        if not isinstance(row, dict):
            raise EntailmentParseError("each assessment must be an object")
        judgement_id = str(row.get("judgement_id", "")).strip()
        label = str(row.get("label", "")).strip()
        verdict = str(row.get("verdict", "")).strip().casefold()
        if verdict not in VERDICTS:
            raise EntailmentParseError("verdict must be one of the three allowed values")
        key = (judgement_id, label)
        if key not in allowed or key in seen:
            # A verdict on something that was never asked about is dropped, not trusted.
            continue
        seen.add(key)
        reason = " ".join(str(row.get("reason", "")).split())[:MAX_REASON_CHARS]
        kept.append(CitationEntailment(judgement_id, label, verdict, reason))
    return tuple(kept)
