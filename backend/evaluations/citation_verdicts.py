"""Read exported human citation verdicts from saved application reports.

This dataset is separate from the CLI's evaluation-run `review.json` labels: it comes
from reviewers using the report reader on real saved reports. Every verdict is a human
opinion, not ground truth. The reader validates each row's exact-version and excerpt
bindings, then reports counts per verdict and relation with explicit denominators. It
never computes a single accuracy figure.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from ase.domain.citation_verdict_export import binding_digest
from ase.domain.citation_verdicts import MAX_VERDICT_NOTE, VERDICT_DATASET, CitationVerdictValue

MAX_EXPORT_BYTES = 64_000_000
VERDICTS = tuple(value.value for value in CitationVerdictValue)
RELATIONS = ("supporting", "contradicting")
ATTRIBUTION = (
    "Human opinions recorded by reviewers on saved application reports. They are not ground "
    "truth and are kept separate from evaluation-run human review labels."
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _uuid(value: object) -> str:
    _require(type(value) is str, "Identifiers must be text.")
    return str(UUID(str(value)))


def _check_excerpt(excerpt: object) -> None:
    if excerpt is None:
        return
    if not isinstance(excerpt, dict):
        raise ValueError("An excerpt must be an object or null.")
    text, start, end = excerpt.get("text"), excerpt.get("start"), excerpt.get("end")
    if not (isinstance(text, str) and type(start) is int and type(end) is int):
        raise ValueError("Invalid excerpt.")
    _require(0 <= start <= end and end - start == len(text), "Excerpt offsets do not match.")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    _require(excerpt.get("sha256") == digest, "Excerpt hash does not match its text.")


def _check_row(row: Mapping[str, Any], header: Mapping[str, Any]) -> None:
    _require(row.get("record") == "verdict", "Every row after the header is a verdict.")
    _require(row.get("dataset") == VERDICT_DATASET, "Verdict rows belong to another dataset.")
    _uuid(row.get("verdict_id"))
    _uuid(row.get("reviewer_id"))
    for name in ("report_id", "report_version_id", "version_number"):
        _require(row.get(name) == header.get(name), "A verdict is bound to another version.")
    _require(row.get("verdict") in VERDICTS, "Unknown verdict value.")
    _require(row.get("relation") in RELATIONS, "Unknown citation relation.")
    for name in ("judgement_id", "label"):
        value = row.get(name)
        _require(type(value) is str and 0 < len(value) <= 200, "Invalid citation anchor.")
    note = row.get("note")
    _require(note is None or (type(note) is str and len(note) <= MAX_VERDICT_NOTE), "Invalid note.")
    _require(type(row.get("current")) is bool, "Invalid current marker.")
    _require(type(row.get("team_scoped")) is bool, "Invalid scope marker.")
    datetime.fromisoformat(str(row.get("recorded_at")))
    _check_excerpt(row.get("excerpt"))
    _require(row.get("binding_sha256") == binding_digest(row), "A verdict binding was altered.")


def load_verdict_export(lines: Iterable[str]) -> list[dict[str, Any]]:
    """Validate one export: its header, then exactly the declared number of bound rows."""
    records = [json.loads(line) for line in lines if line.strip()]
    _require(bool(records), "The export is empty.")
    header = records[0]
    _require(isinstance(header, dict), "The export header is invalid.")
    _require(header.get("record") == "header", "The export must start with its header.")
    _require(header.get("dataset") == VERDICT_DATASET, "This is not a citation verdict export.")
    _uuid(header.get("report_id"))
    _uuid(header.get("report_version_id"))
    _require(type(header.get("version_number")) is int, "Invalid version number.")
    rows = records[1:]
    _require(header.get("verdicts") == len(rows), "The export row count does not match.")
    for row in rows:
        _require(isinstance(row, dict), "Invalid verdict row.")
        _check_row(row, header)
    _require(
        len({row["verdict_id"] for row in rows}) == len(rows), "Duplicate verdict identifiers."
    )
    return rows


def read_verdict_files(paths: Sequence[Path]) -> list[dict[str, Any]]:
    """Merge exports; the same verdict exported twice must be identical apart from currency."""
    merged: dict[str, dict[str, Any]] = {}
    for path in paths:
        _require(path.stat().st_size <= MAX_EXPORT_BYTES, "A verdict export is too large.")
        for row in load_verdict_export(path.read_text(encoding="utf-8").splitlines()):
            previous = merged.get(row["verdict_id"])
            if previous is not None:
                same = {**previous, "current": None} == {**row, "current": None}
                _require(same, "One verdict identifier has conflicting exported content.")
            merged[row["verdict_id"]] = row
    return list(merged.values())


def _citation(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (row["report_version_id"], row["judgement_id"], row["label"], row["relation"])


def _current(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    latest: dict[tuple[str, ...], Mapping[str, Any]] = {}
    ordered = sorted(rows, key=lambda row: (row["recorded_at"], row["verdict_id"]))
    for row in ordered:
        latest[(*_citation(row), row["reviewer_id"])] = row
    return list(latest.values())


def _share(count: int, denominator: int) -> dict[str, Any]:
    return {
        "count": count,
        "denominator": denominator,
        "rate": round(count / denominator, 4) if denominator else None,
    }


def _by_verdict(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["verdict"] for row in rows)
    return {value: _share(counts[value], len(rows)) for value in VERDICTS}


def verdict_metrics(rows: Sequence[Mapping[str, Any]], files: int) -> dict[str, Any]:
    current = _current(rows)
    by_citation: dict[tuple[str, ...], set[str]] = defaultdict(set)
    reviewers: Counter[tuple[str, ...]] = Counter()
    for row in current:
        by_citation[_citation(row)].add(row["verdict"])
        reviewers[_citation(row)] += 1
    reviewed_twice = [citation for citation, count in reviewers.items() if count > 1]
    return {
        "dataset": VERDICT_DATASET,
        "attribution": ATTRIBUTION,
        "files": files,
        "report_versions": len({row["report_version_id"] for row in rows}),
        "verdicts_read": len(rows),
        "superseded_verdicts": len(rows) - len(current),
        "current_verdicts": len(current),
        "citations_with_verdicts": len(by_citation),
        "reviewers": len({row["reviewer_id"] for row in current}),
        "by_verdict": _by_verdict(current),
        "by_relation": {
            relation: _by_verdict([row for row in current if row["relation"] == relation])
            for relation in RELATIONS
        },
        "citations_with_a_does_not_support_verdict": _share(
            sum("does_not_support" in values for values in by_citation.values()),
            len(by_citation),
        ),
        "citations_with_reviewer_disagreement": _share(
            sum(len(by_citation[citation]) > 1 for citation in reviewed_twice),
            len(reviewed_twice),
        ),
        "notice": "Counts are given with their denominators. No single accuracy figure is "
        "computed, and verdicts are human opinions.",
    }
