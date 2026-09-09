"""Strict screening inputs and parsed relevance decisions, never truth assessments."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, cast

Relevance = Literal[
    "armed_conflict", "civil_unrest", "military_activity", "context", "unrelated", "uncertain"
]
RELEVANCE = (
    "armed_conflict",
    "civil_unrest",
    "military_activity",
    "context",
    "unrelated",
    "uncertain",
)
POSITIVE_RELEVANCE = frozenset(RELEVANCE[:4])
MAX_BATCH = 10
MAX_TITLE = 300
MAX_SUMMARY = 1_000
MAX_REASON = 350
MAX_QUOTE = 300
MAX_KEY = 128
MAX_OUTPUT_BYTES = 64 * 1024
POLICY_VERSION = "ase-conflict-screening-v1"


@dataclass(frozen=True, slots=True)
class ScreeningInput:
    key: str
    title: str
    summary: str

    def __post_init__(self) -> None:
        for value, limit, required in (
            (self.key, MAX_KEY, True),
            (self.title, MAX_TITLE, True),
            (self.summary, MAX_SUMMARY, False),
        ):
            if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
                raise ValueError("Screening input exceeds its text bounds.")


@dataclass(frozen=True, slots=True)
class ScreeningVerdict:
    relevance: Relevance
    reason: str
    quote: str


def validate_inputs(items: Sequence[ScreeningInput]) -> None:
    if not 1 <= len(items) <= MAX_BATCH or len({item.key for item in items}) != len(items):
        raise ValueError("Screening requires a bounded batch of unique input keys.")


def screening_schema(items: Sequence[ScreeningInput]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["verdicts"],
        "properties": {
            "verdicts": {
                "type": "array",
                "minItems": len(items),
                "maxItems": len(items),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["key", "relevance", "reason", "quote"],
                    "properties": {
                        "key": {"type": "string", "enum": [item.key for item in items]},
                        "relevance": {"type": "string", "enum": list(RELEVANCE)},
                        "reason": {"type": "string", "minLength": 1, "maxLength": MAX_REASON},
                        "quote": {"type": "string", "maxLength": MAX_QUOTE},
                    },
                },
            }
        },
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate screening JSON key.")
        value[key] = item
    return value


def _invalid_constant(_value: str) -> None:
    raise ValueError("Invalid screening JSON number.")


def parse_verdicts(content: str, items: Sequence[ScreeningInput]) -> dict[str, ScreeningVerdict]:
    """Validate the whole batch before returning any decision; never repair invented IDs."""
    validate_inputs(items)
    if len(content.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("Screening response exceeds its byte budget.")
    data = json.loads(content, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    if not isinstance(data, dict) or set(data) != {"verdicts"}:
        raise ValueError("Invalid screening response object.")
    rows = data["verdicts"]
    if not isinstance(rows, list) or len(rows) != len(items):
        raise ValueError("Screening response count does not match its inputs.")
    inputs = {item.key: item for item in items}
    verdicts: dict[str, ScreeningVerdict] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"key", "relevance", "reason", "quote"}:
            raise ValueError("Invalid screening verdict fields.")
        key, relevance, reason, quote = (
            row[name] for name in ("key", "relevance", "reason", "quote")
        )
        if (
            not isinstance(key, str)
            or key not in inputs
            or key in verdicts
            or not isinstance(relevance, str)
            or relevance not in RELEVANCE
            or not isinstance(reason, str)
            or not 1 <= len(reason.strip()) <= MAX_REASON
            or len(reason) > MAX_REASON
            or not isinstance(quote, str)
            or len(quote) > MAX_QUOTE
        ):
            raise ValueError("Invalid screening verdict values.")
        source = inputs[key]
        supported = bool(quote.strip()) and (quote in source.title or quote in source.summary)
        if (relevance in POSITIVE_RELEVANCE and not supported) or (quote and not supported):
            verdicts[key] = ScreeningVerdict(
                "uncertain",
                "The model supplied no exact supporting excerpt from the source text.",
                "",
            )
        else:
            verdicts[key] = ScreeningVerdict(cast(Relevance, relevance), reason.strip(), quote)
    return verdicts
