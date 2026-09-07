"""Strict structured output for the one bounded continuation assessment."""

from typing import Any


def review_schema(query_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "basis", "rationale", "citations", "gaps", "query"],
        "properties": {
            "decision": {"type": "string", "enum": ["continue", "replan", "sufficient"]},
            "basis": {
                "type": "string",
                "enum": [
                    "empty_results",
                    "potential_conflict",
                    "question_addressed",
                    "insufficient_context",
                ],
            },
            "rationale": {"type": "string", "minLength": 1, "maxLength": 1000},
            "citations": {
                "type": "array",
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["event_id", "source_id", "content_hash", "field", "quote"],
                    "properties": {
                        "event_id": {"type": "string", "maxLength": 128},
                        "source_id": {"type": "string", "maxLength": 120},
                        "content_hash": {"type": "string", "maxLength": 128},
                        "field": {"type": "string", "enum": ["title", "summary"]},
                        "quote": {"type": "string", "minLength": 1, "maxLength": 500},
                    },
                },
            },
            "gaps": {
                "type": "array",
                "maxItems": 8,
                "items": {"type": "string", "minLength": 1, "maxLength": 300},
            },
            "query": {"anyOf": [{"type": "null"}, query_schema]},
        },
    }
