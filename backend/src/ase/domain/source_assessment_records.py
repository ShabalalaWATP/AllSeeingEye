"""Bounded JSON boundary for the pinned A01 report-source assessment contract.

Absent legacy metadata stays absent. Invalid saved data never falls back to live
ratings or newly inferred origin groups. This decoder validates structure and
the pinned grouping rules; storage/actor authenticity remains the host's boundary.
"""

import json
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from enum import IntEnum, StrEnum
from types import UnionType
from typing import Any, Literal, cast, get_args, get_origin, get_type_hints
from uuid import UUID

from ase.domain.source_assessment_report import (
    ReportSourceAssessment,
    SourceAssessmentCapture,
    SourceAssessmentSnapshotError,
)

MAX_SOURCE_ASSESSMENT_BYTES = 4 * 1024 * 1024
MAX_SOURCE_ASSESSMENT_VALUES = 100_000
MAX_SOURCE_ASSESSMENT_DEPTH = 16

__all__ = [
    "SourceAssessmentSnapshotError",
    "source_assessment_capture_from_dict",
    "source_assessment_capture_to_dict",
    "source_assessment_report_from_dict",
    "source_assessment_report_to_dict",
]


def _check_json(value: object) -> None:
    pending = [(value, 0)]
    count, size = 0, 0
    while pending:
        current, depth = pending.pop()
        count += 1
        if count > MAX_SOURCE_ASSESSMENT_VALUES or depth > MAX_SOURCE_ASSESSMENT_DEPTH:
            raise ValueError("Report-source JSON exceeds structural bounds.")
        if type(current) is dict:
            if count + len(pending) + 2 * len(current) > MAX_SOURCE_ASSESSMENT_VALUES:
                raise ValueError("Report-source JSON exceeds mapping bounds.")
            for key, child in current.items():
                if type(key) is not str:
                    raise ValueError("Report-source JSON requires string keys.")
                pending.extend(((key, depth + 1), (child, depth + 1)))
        elif type(current) is list:
            if count + len(pending) + len(current) > MAX_SOURCE_ASSESSMENT_VALUES:
                raise ValueError("Report-source JSON exceeds collection bounds.")
            pending.extend((child, depth + 1) for child in current)
        else:
            size += _scalar_size(current)
        if size + count > MAX_SOURCE_ASSESSMENT_BYTES:
            raise ValueError("Report-source JSON exceeds byte bounds.")


def _scalar_size(value: object) -> int:
    if type(value) is str:
        if len(value) > MAX_SOURCE_ASSESSMENT_BYTES:
            raise ValueError("Report-source JSON exceeds text bounds.")
        return len(value.encode("utf-8")) + 2
    if value is None or type(value) in (bool, int):
        if type(value) is int and abs(value) > 2**31 - 1:
            raise ValueError("Report-source JSON exceeds integer bounds.")
        return 12
    raise ValueError("Report-source records require JSON primitive values.")


def _decode(kind: Any, value: Any) -> Any:
    """Decode only the local contract's declared dataclasses and scalar types."""
    origin, args = get_origin(kind), get_args(kind)
    if origin is UnionType:
        if value is None and type(None) in args:
            return None
        return _decode(next(option for option in args if option is not type(None)), value)
    if origin is tuple:
        if type(value) is not list:
            raise ValueError("Invalid saved assessment collection.")
        return tuple(_decode(args[0], item) for item in value)
    if isinstance(kind, type) and is_dataclass(kind):
        if type(value) is not dict or set(value) != {field.name for field in fields(kind)}:
            raise ValueError("Invalid saved assessment fields.")
        hints = get_type_hints(kind)
        return kind(**{name: _decode(hint, value[name]) for name, hint in hints.items()})
    return _decode_scalar(kind, value)


def _decode_scalar(kind: Any, value: Any) -> Any:
    if get_origin(kind) is Literal:
        if type(value) is not str or value not in get_args(kind):
            raise ValueError("Invalid saved evidence role.")
        return value
    if isinstance(kind, type) and issubclass(kind, StrEnum):
        if type(value) is not str:
            raise ValueError("Invalid saved qualitative assessment category.")
        return kind(value)
    if isinstance(kind, type) and issubclass(kind, IntEnum):
        if type(value) is not int:
            raise ValueError("Invalid saved qualitative assessment category.")
        return kind(value)
    if kind is datetime or kind is UUID:
        if type(value) is not str:
            raise ValueError("Invalid saved assessment date or identifier.")
        return datetime.fromisoformat(value) if kind is datetime else UUID(value)
    if kind in (str, bool, int) and type(value) is kind:
        return value
    raise ValueError("Invalid saved assessment value.")


def source_assessment_report_from_dict(
    data: object, *, required: bool = False
) -> ReportSourceAssessment | None:
    """Restore only frozen metadata; no source registry, model or provider is consulted."""
    if data is None and not required:
        return None
    try:
        _check_json(data)
        return cast(ReportSourceAssessment, _decode(ReportSourceAssessment, data))
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
        raise SourceAssessmentSnapshotError(
            "Invalid or missing frozen source assessment."
        ) from None


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError("Unsupported frozen source-assessment value.")


def source_assessment_report_to_dict(report: ReportSourceAssessment) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(
        json.dumps(asdict(report), default=_json_default, allow_nan=False)
    )
    # Preserve one acceptance boundary for in-memory producers and persisted reads.
    source_assessment_report_from_dict(result, required=True)
    return result


def source_assessment_capture_from_dict(data: object) -> SourceAssessmentCapture:
    """Present metadata must be valid; a present null is not a legacy record."""
    try:
        _check_json(data)
        return cast(SourceAssessmentCapture, _decode(SourceAssessmentCapture, data))
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
        raise SourceAssessmentSnapshotError("Invalid frozen source-assessment receipt.") from None


def source_assessment_capture_to_dict(capture: SourceAssessmentCapture) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(
        json.dumps(asdict(capture), default=_json_default, allow_nan=False)
    )
    source_assessment_capture_from_dict(result)
    return result
