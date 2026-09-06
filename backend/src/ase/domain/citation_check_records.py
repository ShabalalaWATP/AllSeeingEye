"""Saved literal-check decoding, without rerunning heuristics against historic reports."""

from collections.abc import Mapping
from dataclasses import asdict, fields, is_dataclass
from enum import StrEnum
from types import UnionType
from typing import Any, Literal, cast, get_args, get_origin, get_type_hints

from ase.domain.citation_checks import ReportCitationChecks


def citation_checks_to_dict(checks: ReportCitationChecks) -> dict[str, Any]:
    return asdict(checks)


def _category(kind: Any, value: Any) -> Any:
    if not isinstance(value, str):
        raise ValueError("Invalid saved citation-check category")
    if get_origin(kind) is Literal:
        if value not in get_args(kind):
            raise ValueError("Invalid saved citation-check category")
        return value
    return kind(value)


def _decode(kind: Any, value: Any) -> Any:
    origin, args = get_origin(kind), get_args(kind)
    if origin is UnionType:
        if value is None and type(None) in args:
            return None
        return _decode(next(option for option in args if option is not type(None)), value)
    if origin is Literal or (isinstance(kind, type) and issubclass(kind, StrEnum)):
        return _category(kind, value)
    if origin is tuple:
        if not isinstance(value, list | tuple):
            raise ValueError("Invalid saved citation-check collection")
        return tuple(_decode(args[0], item) for item in value)
    if isinstance(kind, type) and is_dataclass(kind):
        if not isinstance(value, Mapping) or set(value) != {field.name for field in fields(kind)}:
            raise ValueError("Invalid saved citation-check fields")
        return kind(
            **{name: _decode(hint, value[name]) for name, hint in get_type_hints(kind).items()}
        )
    if kind in (str, int) and type(value) is kind:
        return value
    raise ValueError("Invalid saved citation-check value")


def citation_checks_from_dict(data: Mapping[str, Any] | None) -> ReportCitationChecks | None:
    """Legacy absence remains None; malformed stored checks are not silently repaired."""
    return None if data is None else cast(ReportCitationChecks, _decode(ReportCitationChecks, data))
