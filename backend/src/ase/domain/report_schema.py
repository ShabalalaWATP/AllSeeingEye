"""The JSON schema for the report body, handed to the model as its response format."""

from __future__ import annotations

from typing import Any

from ase.domain.doctrine import Confidence, Probability
from ase.domain.reports import ChangeFromPrevious, WatchCondition


def _string_list() -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}}


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
            "type": "array",
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
                    "indicators",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "statement": {"type": "string"},
                    "probability": {"type": "string", "enum": [p.value for p in Probability]},
                    "confidence": {"type": "string", "enum": [c.value for c in Confidence]},
                    "confidence_statement": {"type": "string"},
                    "supporting_evidence": _string_list(),
                    "contradicting_evidence": _string_list(),
                    "assumptions": _string_list(),
                    "change_from_previous": {
                        "type": ["string", "null"],
                        "enum": [*[c.value for c in ChangeFromPrevious], None],
                    },
                    "indicators": _string_list(),
                },
            },
        },
        "reporting": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["theme", "items"],
                "properties": {
                    "theme": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["text", "evidence", "grade"],
                            "properties": {
                                "text": {"type": "string"},
                                "evidence": _string_list(),
                                "grade": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "assessment": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["heading", "text", "evidence"],
                "properties": {
                    "heading": {"type": "string"},
                    "text": {"type": "string"},
                    "evidence": _string_list(),
                },
            },
        },
        "assumptions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "text", "lynchpin"],
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "lynchpin": {"type": "boolean"},
                },
            },
        },
        "alternative_hypotheses": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "why_less_likely", "evidence"],
                "properties": {
                    "text": {"type": "string"},
                    "why_less_likely": {"type": "string"},
                    "evidence": _string_list(),
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
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "eei"],
                "properties": {"text": {"type": "string"}, "eei": {"type": ["string", "null"]}},
            },
        },
        "collection_recommendations": _string_list(),
        "sourcing_statement": {"type": "string"},
    },
}
