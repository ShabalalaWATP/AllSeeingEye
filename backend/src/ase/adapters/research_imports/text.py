"""Strict UTF-8, CSV and JSON extraction with reproducible source locators."""

from __future__ import annotations

import csv
import io
import json
import math
from collections.abc import Iterator
from typing import Any

from ase.adapters.research_imports.models import (
    MAX_DEPTH,
    MAX_NODES,
    MAX_ROWS,
    ImportRejected,
    TextBudget,
)


def decode_text(data: bytes) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportRejected("Text imports must be valid UTF-8.") from None
    if any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        raise ImportRejected("Text import contains unsupported control characters.")
    return text


def extract_text(data: bytes, budget: TextBudget) -> tuple[str, ...]:
    for number, line in enumerate(decode_text(data).splitlines(), 1):
        budget.add(f"line {number}", line)
    return ("Plain text has no verified author, publication date or formatting provenance.",)


def extract_csv(data: bytes, budget: TextBudget) -> tuple[str, ...]:
    reader = csv.reader(io.StringIO(decode_text(data), newline=""), strict=True)
    previous_line = 0
    try:
        for number, row in enumerate(reader, 1):
            if number > MAX_ROWS or len(row) > 100:
                raise ImportRejected("CSV exceeds the row or column limit.")
            reference = f"CSV row {number}, lines {previous_line + 1}-{reader.line_num}"
            previous_line = reader.line_num
            # Quoting is retained in an unambiguous JSON array; formulas are never evaluated.
            budget.add(reference, json.dumps(row, ensure_ascii=False))
    except csv.Error:
        raise ImportRejected("CSV is malformed or contains an oversized field.") from None
    return (
        "CSV rows count logical records, including any header; physical line ranges are retained.",
        "Cells are extracted as text. Formulae, types, units and column meanings are not inferred.",
    )


def check_json_depth(text: str) -> None:
    """Bound nesting before json.loads can recurse or allocate a nested object tree."""
    depth = 0
    quoted = False
    escaped = False
    separators = 0
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise ImportRejected("JSON exceeds the nesting limit.")
        elif char in "]}":
            depth -= 1
        elif char in ",:":
            separators += 1
            if separators > MAX_NODES:
                raise ImportRejected("JSON exceeds the element limit.")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ImportRejected("JSON contains duplicate object keys.")
        value[key] = item
    return value


def _reject_constant(_: str) -> None:
    raise ImportRejected("JSON contains a non-finite numeric value.")


def _finite_float(text: str) -> float:
    number = float(text)
    if not math.isfinite(number):
        raise ImportRejected("JSON contains a non-finite numeric value.")
    return number


def _leaves(value: object) -> Iterator[tuple[str, object]]:
    pending = [("", value)]
    visited = 0
    while pending:
        pointer, current = pending.pop()
        visited += 1
        if visited + len(pending) > MAX_NODES:
            raise ImportRejected("JSON exceeds the element limit.")
        if isinstance(current, dict) and current:
            if len(current) > MAX_NODES:
                raise ImportRejected("JSON exceeds the element limit.")
            for key, item in reversed(list(current.items())):
                escaped_key = str(key).replace("~", "~0").replace("/", "~1")
                pending.append((f"{pointer}/{escaped_key}", item))
        elif isinstance(current, list) and current:
            if len(current) > MAX_ROWS:
                raise ImportRejected("JSON array exceeds the row limit.")
            pending.extend((f"{pointer}/{i}", current[i]) for i in reversed(range(len(current))))
        else:
            yield pointer, current


def extract_json(data: bytes, budget: TextBudget) -> tuple[str, ...]:
    text = decode_text(data)
    check_json_depth(text)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, ImportRejected):
            raise
        raise ImportRejected("JSON is malformed or contains an unsupported value.") from None
    for pointer, leaf in _leaves(value):
        # JSON Pointer identifies the exact value without assuming a dataset schema.
        if len(pointer) > 300:
            raise ImportRejected("JSON source locator exceeds the length limit.")
        reference = f"JSON pointer {pointer}" if pointer else "JSON root (empty pointer)"
        serialised = json.dumps(leaf, ensure_ascii=False, allow_nan=False)
        # JSON escape syntax permits lone surrogates that cannot become valid UTF-8
        # evidence or hashes. Reject them before returning a worker result.
        try:
            reference.encode("utf-8")
            serialised.encode("utf-8")
        except UnicodeEncodeError:
            raise ImportRejected("JSON contains an invalid Unicode value.") from None
        budget.add(reference, serialised)
    return (
        "JSON locations use RFC 6901 pointers; array indexes start at zero.",
        "Values are extracted without inferring identities, dates, units or relationships.",
    )
