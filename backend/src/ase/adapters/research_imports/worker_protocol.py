"""Validate bounded JSON received from a disposable parser, never unpickle it."""

from __future__ import annotations

import json
from typing import Any

from ase.adapters.research_imports import MEDIA_TYPES
from ase.adapters.research_imports.models import (
    MAX_TEXT_CHARS,
    MAX_UNIT_CHARS,
    MAX_UNITS,
    ExtractedUnit,
    ExtractionResult,
    ImportRejected,
)
from ase.adapters.research_imports.text import check_json_depth


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ImportRejected("The parser returned an ambiguous response.")
        value[key] = item
    return value


def _string(value: object, limit: int, *, blank: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or (not blank and not value.strip()):
        raise ImportRejected("The parser returned invalid evidence.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ImportRejected("The parser returned invalid evidence.") from None
    return value


def validate_result(data: bytes, filename: str, expected_hash: str) -> ExtractionResult:
    """Recheck every output budget and bind provenance to the submitted bytes."""
    try:
        check_json_depth(data.decode("utf-8"))
        response = json.loads(data, object_pairs_hook=_object)
    except (ValueError, RecursionError):
        raise ImportRejected("The parser returned an invalid response.") from None
    if not isinstance(response, dict) or type(response.get("ok")) is not bool:
        raise ImportRejected("The parser returned an invalid response.")
    if response["ok"] is False:
        if response.get("error") == "resource_limits":
            raise ImportRejected("Required document parser resource limits are unavailable.")
        raise ImportRejected("Document extraction failed or exceeded a supported limit.")
    value = response.get("result")
    fields = {"filename", "media_type", "sha256", "units", "limitations"}
    if set(response) != {"ok", "result"} or not isinstance(value, dict) or set(value) != fields:
        raise ImportRejected("The parser returned invalid evidence.")
    if value["filename"] != filename or value["sha256"] != expected_hash:
        raise ImportRejected("The parser returned mismatched document provenance.")
    expected_type = MEDIA_TYPES.get("." + filename.rsplit(".", 1)[-1].lower())
    if value["media_type"] != expected_type or expected_type is None:
        raise ImportRejected("The parser returned an invalid document type.")
    rows = value["units"]
    limitations = value["limitations"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_UNITS:
        raise ImportRejected("The parser returned an invalid passage count.")
    if not isinstance(limitations, list) or not 1 <= len(limitations) <= 20:
        raise ImportRejected("The parser returned invalid extraction limitations.")
    notes = tuple(_string(note, 500) for note in limitations)
    units: list[ExtractedUnit] = []
    references: set[str] = set()
    characters = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"reference", "text"}:
            raise ImportRejected("The parser returned an invalid passage.")
        reference = _string(row["reference"], 400)
        text = _string(row["text"], MAX_UNIT_CHARS)
        characters += len(text)
        if characters > MAX_TEXT_CHARS or reference in references:
            raise ImportRejected("The parser returned excessive or duplicate passages.")
        references.add(reference)
        units.append(ExtractedUnit(reference, text))
    return ExtractionResult(filename, expected_type, expected_hash, tuple(units), notes)
