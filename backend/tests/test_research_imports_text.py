"""Imports preserve exact locators and reject ambiguous or excessive source content."""

from __future__ import annotations

import hashlib
import json
import pickle
from datetime import UTC, datetime

import pytest

from ase.adapters.research_imports import events_from_extraction, extract_upload
from ase.adapters.research_imports.models import MAX_UPLOAD_BYTES, ImportRejected, TextBudget


def test_text_keeps_line_numbers_chunks_and_original_hash() -> None:
    source = ("\ufeffFirst line\r\n\r\n" + "x" * 1_801).encode()
    result = extract_upload(source, "notes.TXT")
    assert result.sha256 == hashlib.sha256(source).hexdigest()
    assert [unit.reference for unit in result.units] == [
        "line 1",
        "line 3, characters 1-1800",
        "line 3, characters 1801-1801",
    ]
    assert result.units[0].text == "First line"
    # The worker result contains plain dataclasses, not unpicklable Event mapping proxies.
    assert pickle.loads(pickle.dumps(result)) == result  # noqa: S301


def test_csv_preserves_logical_rows_and_multiline_physical_ranges() -> None:
    source = b'name,note\r\nA,"first\nsecond"\r\nB,=SUM(A1)\r\n'
    result = extract_upload(source, "data.csv")
    assert [unit.reference for unit in result.units] == [
        "CSV row 1, lines 1-1",
        "CSV row 2, lines 2-3",
        "CSV row 3, lines 4-4",
    ]
    assert json.loads(result.units[1].text) == ["A", "first\nsecond"]
    assert json.loads(result.units[2].text)[1] == "=SUM(A1)"


def test_json_pointers_are_exact_and_empty_containers_not_lost() -> None:
    result = extract_upload(b'{"a/b~c": [{"value": 1.25}, null], "empty": {}}', "data.json")
    assert [unit.reference for unit in result.units] == [
        "JSON pointer /a~1b~0c/0/value",
        "JSON pointer /a~1b~0c/1",
        "JSON pointer /empty",
    ]
    assert [unit.text for unit in result.units] == ["1.25", "null", "{}"]
    assert extract_upload(b'"[[[escaped \\" text"', "scalar.json").units[0].reference == (
        "JSON root (empty pointer)"
    )


@pytest.mark.parametrize(
    ("source", "name", "reason"),
    [
        (b"", "a.txt", "empty"),
        (b"a" * (MAX_UPLOAD_BYTES + 1), "a.txt", "8 MiB"),
        (b"hello", "../a.txt", "plain filename"),
        (b"hello", "C:\\a.txt", "plain filename"),
        (b"hello", "a\x00.txt", "plain filename"),
        (b"hello", "a" * 121, "plain filename"),
        (b"hello", "image.png", "Supported imports"),
        (b"\xff", "a.txt", "UTF-8"),
        (b"x\x00y", "a.txt", "control"),
        (b" \n\t", "a.txt", "No text"),
        (b'"unclosed', "a.csv", "malformed"),
        (b"a\n" * 201, "a.csv", "row or column"),
        (b"," * 100, "a.csv", "row or column"),
        (b'{"x": 1,"x": 2}', "a.json", "duplicate"),
        (b"NaN", "a.json", "non-finite"),
        (b"1e9999", "a.json", "non-finite"),
        (b'"\\ud800"', "a.json", "Unicode"),
        (b"[", "a.json", "malformed"),
        (b"[" * 33 + b"0" + b"]" * 33, "a.json", "nesting"),
        (b"[" + b"0," * 200 + b"0]", "a.json", "row limit"),
        (b"[" + b"0," * 20_001 + b"0]", "a.json", "element limit"),
        (b'{"' + b"x" * 301 + b'": 1}', "a.json", "locator"),
    ],
    ids=lambda value: f"{len(value)}bytes" if isinstance(value, bytes) else str(value),
)
def test_invalid_uploads_have_safe_bounded_errors(source: bytes, name: str, reason: str) -> None:
    with pytest.raises(ImportRejected, match=reason):
        extract_upload(source, name)


def test_output_caps_fail_instead_of_silently_dropping_evidence() -> None:
    with pytest.raises(ImportRejected, match="passage limit"):
        extract_upload(b"a\n" * 201, "large.txt")
    with pytest.raises(ImportRejected, match="character limit"):
        extract_upload(b"a" * 200_001, "large.txt")
    budget = TextBudget()
    budget.add("line 1", " \t")
    assert budget.units == []


def test_import_events_are_unassessed_private_passages_with_capture_time() -> None:
    result = extract_upload(b"Unverified claim", "statement.txt")
    captured_at = datetime(2026, 9, 6, tzinfo=UTC)
    events = events_from_extraction(result, captured_at)
    event = events[0]
    assert event.grade == "F6"
    assert event.url is None and event.point is None
    assert event.language == "und"
    assert event.published_at == captured_at == event.observed_at
    assert event.attributes["timestamp_basis"] == "capture time; original publication time unknown"
    assert event.attributes["source_reference"] == "line 1"
    assert event.attributes["original_sha256"] == result.sha256
    assert event.summary == "Unverified claim"
    assert events_from_extraction(result, captured_at)[0].id == event.id
    with pytest.raises(ImportRejected, match="timezone"):
        events_from_extraction(result, datetime(2026, 9, 6))
