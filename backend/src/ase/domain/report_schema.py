"""The JSON schema for the report body, handed to the model as its response format."""

from __future__ import annotations

from typing import Any

from ase.domain.doctrine import Confidence, Probability
from ase.domain.reports import (
    MAX_ITEM_CHARS,
    MAX_JUDGEMENT_CHARS,
    MAX_LIST,
    MAX_SECTION_CHARS,
    ChangeFromPrevious,
    WatchCondition,
)


def _text(limit: int = MAX_ITEM_CHARS, *, required: bool = True) -> dict[str, Any]:
    return {"type": "string", "minLength": int(required), "maxLength": limit}


def _string_list(limit: int = MAX_ITEM_CHARS) -> dict[str, Any]:
    return {"type": "array", "maxItems": MAX_LIST, "items": _text(limit)}


def _evidence_ids() -> dict[str, Any]:
    return {
        **_string_list(32),
        "items": {
            **_text(32),
            "pattern": "^E[1-9][0-9]*$",
            "description": "Exact supplied evidence ID only, for example E1. No explanatory text.",
        },
    }


REPORT_BODY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "key_judgements",
        "reporting",
        "assessment",
        "assumptions",
        "alternative_hypotheses",
        "indicators_and_warning",
        "gaps",
        "collection_recommendations",
        "sourcing_statement",
    ],
    "properties": {
        "key_judgements": {
            "minItems": 1,
            "type": "array",
            "maxItems": MAX_LIST,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "statement",
                    "probability",
                    "confidence",
                    "confidence_statement",
                    "supporting_evidence",
                    "contradicting_evidence",
                    "assumptions",
                    "change_from_previous",
                    "indicators",
                ],
                "properties": {
                    "id": _text(16),
                    "statement": _text(MAX_JUDGEMENT_CHARS),
                    "probability": {"type": "string", "enum": [p.value for p in Probability]},
                    "confidence": {"type": "string", "enum": [c.value for c in Confidence]},
                    "confidence_statement": _text(),
                    "supporting_evidence": {**_evidence_ids(), "minItems": 1},
                    "contradicting_evidence": _evidence_ids(),
                    "assumptions": _string_list(32),
                    "change_from_previous": {
                        "type": ["string", "null"],
                        "enum": [*[c.value for c in ChangeFromPrevious], None],
                    },
                    "indicators": _string_list(),
                },
            },
        },
        "reporting": {
            "minItems": 1,
            "type": "array",
            "maxItems": MAX_LIST,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["theme", "items"],
                "properties": {
                    "theme": _text(120),
                    "items": {
                        "minItems": 1,
                        "type": "array",
                        "maxItems": MAX_LIST,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["text", "evidence", "grade"],
                            "properties": {
                                "text": _text(),
                                "evidence": {**_evidence_ids(), "minItems": 1},
                                "grade": _text(160, required=False),
                            },
                        },
                    },
                },
            },
        },
        "assessment": {
            "minItems": 1,
            "type": "array",
            "maxItems": MAX_LIST,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["heading", "text", "evidence"],
                "properties": {
                    "heading": _text(120),
                    "text": _text(MAX_SECTION_CHARS),
                    "evidence": {**_evidence_ids(), "minItems": 1},
                },
            },
        },
        "assumptions": {
            "type": "array",
            "maxItems": MAX_LIST,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "text", "lynchpin"],
                "properties": {
                    "id": _text(16),
                    "text": _text(),
                    "lynchpin": {"type": "boolean"},
                },
            },
        },
        "alternative_hypotheses": {
            "type": "array",
            "maxItems": MAX_LIST,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "why_less_likely", "evidence"],
                "properties": {
                    "text": _text(),
                    "why_less_likely": _text(),
                    "evidence": {**_evidence_ids(), "minItems": 1},
                },
            },
        },
        "indicators_and_warning": {
            "type": "object",
            "additionalProperties": False,
            "required": ["watch_condition", "changes"],
            "properties": {
                "watch_condition": {"type": "string", "enum": [w.value for w in WatchCondition]},
                "changes": _string_list(),
            },
        },
        "gaps": {
            "type": "array",
            "maxItems": MAX_LIST,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "eei"],
                "properties": {
                    "text": _text(),
                    "eei": {"type": ["string", "null"], "minLength": 1, "maxLength": 32},
                },
            },
        },
        "collection_recommendations": _string_list(),
        "sourcing_statement": _text(MAX_SECTION_CHARS),
    },
}
