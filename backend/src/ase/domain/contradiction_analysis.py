"""The schema and parsing for one bounded pass explaining how two sources conflict.

The mechanical check already names which sources disagree with a judgement and how
strong each side is. It cannot say what the disagreement is actually about. This is the
shape of the model answer that says so: a point of disagreement per judgement, and
nothing that could replace the report's own words.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

METHOD_VERSION = "ase-contradiction-analysis-v1"
MAX_ROWS = 6
MAX_POINT_CHARS = 200
MAX_EXPLANATION_CHARS = 400

LIMITATIONS = (
    "A model compared the frozen extracts. It did not decide which source is right.",
    "Only the cited extracts were read, not the full source articles.",
)

CONTRADICTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["disagreements"],
    "properties": {
        "disagreements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["judgement_id", "point", "explanation"],
                "properties": {
                    "judgement_id": {"type": "string"},
                    "point": {"type": "string"},
                    "explanation": {"type": "string"},
                },
            },
        }
    },
}


class ContradictionParseError(ValueError):
    """The model's JSON does not fit the schema; the message names the field."""


@dataclass(frozen=True, slots=True)
class Disagreement:
    judgement_id: str
    point: str
    explanation: str


def parse_disagreements(data: Any, allowed: frozenset[str]) -> tuple[Disagreement, ...]:
    """Keep one bounded explanation per judgement that was actually asked about."""
    if not isinstance(data, dict):
        raise ContradictionParseError("the answer must be a JSON object")
    rows = data.get("disagreements")
    if not isinstance(rows, list):
        raise ContradictionParseError("disagreements must be a list")
    kept: list[Disagreement] = []
    seen: set[str] = set()
    for row in rows[:MAX_ROWS]:
        if not isinstance(row, dict):
            raise ContradictionParseError("each disagreement must be an object")
        judgement_id = str(row.get("judgement_id", "")).strip()
        if judgement_id not in allowed or judgement_id in seen:
            continue
        point = " ".join(str(row.get("point", "")).split())[:MAX_POINT_CHARS]
        explanation = " ".join(str(row.get("explanation", "")).split())[:MAX_EXPLANATION_CHARS]
        if not point:
            continue
        seen.add(judgement_id)
        kept.append(Disagreement(judgement_id, point, explanation))
    return tuple(kept)
