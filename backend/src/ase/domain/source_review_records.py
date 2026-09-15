"""Strict bounded JSON records for reviewer histories and their version snapshots."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from ase.domain.source_assessment_records import _check_json, _decode, _json_default
from ase.domain.source_assessment_report import ReportSourceAssessment
from ase.domain.source_reviews import SourceReviewRevision, SourceReviewScope

MAX_SOURCE_REVIEW_BYTES = 16 * 1024
MAX_REVIEW_SNAPSHOT_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class SourceReviewSnapshot:
    id: UUID
    report_id: UUID
    report_version_id: UUID
    scope: SourceReviewScope
    authored_by: UUID
    created_at: datetime
    projection: ReportSourceAssessment
    decision_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (self.id, self.report_id, self.report_version_id, self.authored_by):
            if not isinstance(value, UUID):
                raise ValueError("Invalid reviewed source snapshot identity.")
        if (
            not isinstance(self.scope, SourceReviewScope)
            or not isinstance(self.projection, ReportSourceAssessment)
            or self.projection.report_version_id != self.report_version_id
            or self.projection.frozen_at != self.created_at
            or type(self.decision_ids) is not tuple
            or len(self.decision_ids) > 2048
            or len(set(self.decision_ids)) != len(self.decision_ids)
        ):
            raise ValueError("Invalid exact-version source review snapshot.")
        for decision_id in self.decision_ids:
            UUID(decision_id)


def review_record_to_dict(record: SourceReviewRevision | SourceReviewSnapshot) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(json.dumps(asdict(record), default=_json_default))
    _check_json(data)
    return data


def _encode(
    record: SourceReviewRevision | SourceReviewSnapshot, maximum: int
) -> tuple[str, str, int]:
    payload = json.dumps(review_record_to_dict(record), sort_keys=True, separators=(",", ":"))
    encoded = payload.encode("utf-8")
    if len(encoded) > maximum:
        raise ValueError("Source review record exceeds its retained size limit.")
    return payload, hashlib.sha256(encoded).hexdigest(), len(encoded)


def encode_source_review(record: SourceReviewRevision) -> tuple[str, str, int]:
    return _encode(record, MAX_SOURCE_REVIEW_BYTES)


def encode_review_snapshot(record: SourceReviewSnapshot) -> tuple[str, str, int]:
    return _encode(record, MAX_REVIEW_SNAPSHOT_BYTES)


def _read(payload: str, digest: str, size: int, maximum: int) -> object:
    if type(payload) is not str or len(payload) > maximum or type(size) is not int:
        raise ValueError("Invalid bounded source review payload.")
    encoded = payload.encode("utf-8")
    if len(encoded) != size or size > maximum or hashlib.sha256(encoded).hexdigest() != digest:
        raise ValueError("Source review integrity check failed.")
    data = json.loads(payload)
    _check_json(data)
    return data


def decode_source_review(payload: str, digest: str, size: int) -> SourceReviewRevision:
    return cast(
        SourceReviewRevision,
        _decode(SourceReviewRevision, _read(payload, digest, size, MAX_SOURCE_REVIEW_BYTES)),
    )


def decode_review_snapshot(payload: str, digest: str, size: int) -> SourceReviewSnapshot:
    return cast(
        SourceReviewSnapshot,
        _decode(SourceReviewSnapshot, _read(payload, digest, size, MAX_REVIEW_SNAPSHOT_BYTES)),
    )
