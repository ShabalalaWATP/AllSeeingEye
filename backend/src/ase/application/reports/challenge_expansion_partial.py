"""Bounded, frozen source results committed beside a challenge ledger settlement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from ase.application.report_jobs.codec_boundary import boundary, json_copy
from ase.application.report_jobs.collection_records import evidence_from_json
from ase.domain.evidence import EvidenceItem
from ase.domain.report_records import evidence_to_list
from ase.domain.research import CollectionAttempt, CollectionStatus

VERSION = "ase-challenge-partial-v1"
KEY = "challenge_expansion_partial"


@dataclass(frozen=True, slots=True)
class PartialResult:
    request_key: str
    evidence: tuple[EvidenceItem, ...]
    attempt: CollectionAttempt


def encode_partial(rows: tuple[PartialResult, ...], fingerprint: str) -> dict[str, Any]:
    value = cast(
        "dict[str, Any]",
        json_copy(
            {
                "version": VERSION,
                "plan_fingerprint": fingerprint,
                "results": [
                    {
                        "request_key": row.request_key,
                        "evidence": evidence_to_list(row.evidence),
                        "attempt": {
                            "source_id": row.attempt.source_id,
                            "source_name": row.attempt.source_name,
                            "status": row.attempt.status.value,
                            "result_count": row.attempt.result_count,
                            "explanation": row.attempt.explanation,
                            "task_id": row.attempt.task_id,
                        },
                    }
                    for row in rows
                ],
            }
        ),
    )
    decode_partial(value, fingerprint)
    return value


def decode_partial(value: Any, fingerprint: str) -> tuple[PartialResult, ...]:
    if value is None:
        return ()
    data = boundary(value, {"version", "plan_fingerprint", "results"})
    results = data["results"]
    if (
        data["version"] != VERSION
        or data["plan_fingerprint"] != fingerprint
        or type(results) is not list
        or len(results) > 6
    ):
        raise ValueError("Invalid challenge partial checkpoint")
    output: list[PartialResult] = []
    keys: set[str] = set()
    labels: set[str] = set()
    ids: set[str] = set()
    for raw in results:
        row = boundary(raw, {"request_key", "evidence", "attempt"})
        key = row["request_key"]
        receipt = boundary(
            row["attempt"],
            {"source_id", "source_name", "status", "result_count", "explanation", "task_id"},
        )
        if (
            type(key) is not str
            or not key.startswith("challenge:")
            or len(key) != 74
            or key in keys
            or type(row["evidence"]) is not list
            or len(row["evidence"]) > 12
            or any(
                type(receipt[name]) is not str or not 1 <= len(receipt[name]) <= limit
                for name, limit in (("source_id", 120), ("source_name", 200))
            )
            or receipt["status"] not in {"completed", "empty", "failed", "timed_out"}
            or type(receipt["result_count"]) is not int
            or receipt["result_count"] < 0
            or receipt["result_count"] > 12
            or type(receipt["explanation"]) is not str
            or len(receipt["explanation"]) > 1000
            or (
                receipt["task_id"] is not None
                and (type(receipt["task_id"]) is not str or len(receipt["task_id"]) > 160)
            )
        ):
            raise ValueError("Invalid challenge partial result")
        evidence = evidence_from_json(row["evidence"])
        if receipt["result_count"] != len(evidence):
            raise ValueError("Challenge partial receipt does not match evidence")
        if any(item.label in labels or item.event_id in ids for item in evidence):
            raise ValueError("Duplicate frozen challenge evidence")
        keys.add(key)
        labels.update(item.label for item in evidence)
        ids.update(item.event_id for item in evidence)
        output.append(
            PartialResult(
                key,
                evidence,
                CollectionAttempt(
                    receipt["source_id"],
                    receipt["source_name"],
                    CollectionStatus(receipt["status"]),
                    receipt["result_count"],
                    receipt["explanation"],
                    task_id=receipt["task_id"],
                ),
            )
        )
    if len(ids) > 12:
        raise ValueError("Challenge partial exceeds selected evidence cap")
    return tuple(output)
