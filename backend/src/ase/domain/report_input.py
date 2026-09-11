"""Strict boundary for new model responses, separate from historic report decoding."""

from __future__ import annotations

import re
from typing import Any

from ase.domain.report_schema import REPORT_BODY_SCHEMA
from ase.domain.reports import ReportBody, ReportParseError, parse_body


def _check(value: Any, schema: dict[str, Any], path: str) -> None:
    kinds = schema["type"]
    kinds = [kinds] if isinstance(kinds, str) else kinds
    matches = {
        "null": value is None,
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }
    if not any(matches[kind] for kind in kinds):
        raise ReportParseError(f"{path} must have type {' or '.join(kinds)}")
    if "enum" in schema and value not in schema["enum"]:
        raise ReportParseError(f"{path} has an unsupported value")
    if isinstance(value, dict):
        properties = schema["properties"]
        missing = set(schema.get("required", ())) - value.keys()
        unknown = value.keys() - properties.keys()
        if missing or unknown:
            # Report field names from the trusted schema, not arbitrary model keys.
            detail = f"missing {', '.join(sorted(missing))}" if missing else "unknown fields"
            raise ReportParseError(f"{path}: {detail}")
        for key, child in value.items():
            _check(child, properties[key], f"{path}.{key}")
    elif isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 20):
            raise ReportParseError(f"{path} has an invalid number of items")
        for index, item in enumerate(value):
            _check(item, schema["items"], f"{path}[{index}]")
    elif isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value.strip()) <= schema.get("maxLength", 1200):
            raise ReportParseError(f"{path} has an invalid text length")
        # Patterns come only from the application-owned schema, never from model output.
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise ReportParseError(f"{path} has an invalid identifier")


def parse_model_body(data: Any) -> ReportBody:
    """Reject omission, coercion and truncation before parsing a new assessment.

    Persisted failed or historic records continue to use the tolerant ``parse_body``.
    This boundary uses the same schema supplied to the model so its requirements
    cannot silently diverge from those checked by the application.
    """
    _check(data, REPORT_BODY_SCHEMA, "report")
    return parse_body(data)
