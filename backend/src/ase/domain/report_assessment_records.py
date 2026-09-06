"""Strict saved-assessment decoding without running current scoring policy on history."""

from collections.abc import Mapping
from dataclasses import asdict, fields, is_dataclass
from enum import StrEnum
from types import UnionType
from typing import Any, Literal, cast, get_args, get_origin, get_type_hints

from ase.domain.evidence_matrix import ReportAssessment


def assessment_to_dict(assessment: ReportAssessment) -> dict[str, Any]:
    return asdict(assessment)


def _category(kind: Any, value: Any) -> Any:
    if get_origin(kind) is Literal:
        if type(value) is not str or value not in get_args(kind):
            raise ValueError("Invalid saved assessment category")
        return value
    if not isinstance(value, str):
        raise ValueError("Invalid saved assessment enum")
    return kind(value)


def _decode(kind: Any, value: Any) -> Any:
    """Only decode the primitive, enum, tuple and dataclass types in this saved contract."""
    origin, args = get_origin(kind), get_args(kind)
    if origin is UnionType:
        if value is None and type(None) in args:
            return None
        return _decode(next(option for option in args if option is not type(None)), value)
    if origin is Literal or (isinstance(kind, type) and issubclass(kind, StrEnum)):
        return _category(kind, value)
    if origin is tuple:
        if not isinstance(value, list | tuple):
            raise ValueError("Invalid saved assessment collection")
        return tuple(_decode(args[0], item) for item in value)
    if isinstance(kind, type) and is_dataclass(kind):
        if not isinstance(value, Mapping) or set(value) != {field.name for field in fields(kind)}:
            raise ValueError("Invalid saved assessment fields")
        hints = get_type_hints(kind)
        return kind(**{name: _decode(hint, value[name]) for name, hint in hints.items()})
    if kind in (str, bool, int) and type(value) is kind:
        return value
    raise ValueError("Invalid saved assessment value")


def assessment_from_dict(data: Mapping[str, Any] | None) -> ReportAssessment | None:
    """Absent historical assessments remain absent; malformed saved scores are never coerced."""
    if data is None:
        return None
    return cast(ReportAssessment, _decode(ReportAssessment, data))
