"""Deterministic comparison of structured report content and frozen evidence."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from ase.application.reports.document import build_document
from ase.domain.report_documents import ChangeKind, ReportChange, ReportComparison
from ase.domain.report_records import ReportRecord, ReportVersion


def _leaves(value: Any, path: str = "") -> dict[str, str]:
    if isinstance(value, dict):
        leaves: dict[str, str] = {}
        for key in sorted(value):
            leaves.update(_leaves(value[key], f"{path}.{key}" if path else str(key)))
        return leaves
    if isinstance(value, list | tuple):
        leaves = {}
        for index, item in enumerate(value, 1):
            leaves.update(_leaves(item, f"{path}[{index}]"))
        return leaves
    return {path: value if isinstance(value, str) else json.dumps(value, default=str)}


def _changes(section: str, before: dict[str, str], after: dict[str, str]) -> list[ReportChange]:
    changes = []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        kind = (
            ChangeKind.ADDED
            if old is None
            else ChangeKind.REMOVED
            if new is None
            else ChangeKind.CHANGED
        )
        changes.append(ReportChange(section, path, kind, old, new))
    return changes


def compare_versions(
    record: ReportRecord, before: ReportVersion, after: ReportVersion
) -> ReportComparison:
    # Bound the same persisted inputs before producing potentially large diff responses.
    build_document(record, before)
    build_document(record, after)
    changes = _changes("Content", _leaves(asdict(before.body)), _leaves(asdict(after.body)))
    for section, old, new in (
        ("Direction", before.direction, after.direction),
        ("Devil's advocacy", before.advocacy, after.advocacy),
        ("Automated evidence assessment", before.assessment, after.assessment),
        ("Literal citation checks", before.citation_checks, after.citation_checks),
        ("Collection coverage", before.research, after.research),
        ("Judgement challenge", before.challenge, after.challenge),
        ("Research context", before.research_context, after.research_context),
    ):
        changes.extend(
            _changes(
                section, _leaves(asdict(old)) if old else {}, _leaves(asdict(new)) if new else {}
            )
        )
    changes.extend(
        _changes(
            "Validation",
            _leaves({"status": before.status, "findings": [asdict(f) for f in before.findings]}),
            _leaves({"status": after.status, "findings": [asdict(f) for f in after.findings]}),
        )
    )
    # Labels are local to each version. Match by event ID so relabelling cannot hide
    # replacement evidence, and include grades, hashes and capture provenance in changes.
    old_items = {item.event_id: item for item in before.evidence}
    new_items = {item.event_id: item for item in after.evidence}
    for event_id in sorted(old_items.keys() | new_items.keys()):
        old_item, new_item = old_items.get(event_id), new_items.get(event_id)
        prefix = new_item.label if new_item else old_items[event_id].label
        changes.extend(
            _changes(
                "Evidence",
                _leaves(asdict(old_item), f"{prefix} ({event_id})") if old_item else {},
                _leaves(asdict(new_item), f"{prefix} ({event_id})") if new_item else {},
            )
        )
    return ReportComparison(before.number, after.number, tuple(changes))
