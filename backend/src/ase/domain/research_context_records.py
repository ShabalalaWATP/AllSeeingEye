"""Strict bounded saved-context codec, never re-projecting historical evidence."""

from collections.abc import Mapping
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from types import UnionType
from typing import Any, Literal, cast, get_args, get_origin, get_type_hints

from ase.domain.evidence_attributes import EvidenceAttribute, evidence_attributes_from_list
from ase.domain.research_context import MAX_CONTEXT_ITEMS, ResearchContext

COLLECTION_LIMITS = {
    "timeline": MAX_CONTEXT_ITEMS,
    "identity_candidates": MAX_CONTEXT_ITEMS,
    "source_chains": MAX_CONTEXT_ITEMS * 3,
    "source_relationships": MAX_CONTEXT_ITEMS * (MAX_CONTEXT_ITEMS - 1) // 2,
    "identifiers": 6,
    "aliases": 6,
    "temporal_attributes": 4,
    "limitations": 16,
    "reasons": 8,
}
SHORT_FIELDS = frozenset({"method_version", "evidence_label", "evidence_labels", "namespace"})


def _decode_collection(args: tuple[Any, ...], value: Any, name: str) -> tuple[Any, ...]:
    if not isinstance(value, list | tuple) or len(value) > COLLECTION_LIMITS.get(name, 40):
        raise ValueError("Invalid saved research context collection")
    if args[-1] is not Ellipsis:
        if len(value) != len(args):
            raise ValueError("Invalid saved research context pair")
        return tuple(
            _decode(subtype, item, name) for subtype, item in zip(args, value, strict=True)
        )
    return tuple(_decode(args[0], item, name) for item in value)


def _decode_scalar(kind: Any, value: Any, name: str) -> Any:
    if kind is datetime:
        if not isinstance(value, str) or len(value) > 64 or "T" not in value:
            raise ValueError("Invalid saved research context timestamp")
        # Preserve explicit offsets and naive legacy dates; never assume a missing timezone.
        return datetime.fromisoformat(value)
    if kind is str and type(value) is str:
        maximum = 64 if name in SHORT_FIELDS else 2000
        if len(value) > maximum or (name in SHORT_FIELDS and not value.strip()):
            raise ValueError("Invalid saved research context text")
        return value
    if kind is bool and type(value) is bool:
        return value
    raise ValueError("Invalid saved research context value")


def _decode(kind: Any, value: Any, name: str = "") -> Any:
    origin, args = get_origin(kind), get_args(kind)
    if origin is UnionType:
        return (
            None
            if value is None and type(None) in args
            else _decode(next(option for option in args if option is not type(None)), value, name)
        )
    if origin is Literal:
        if type(value) is not str or value not in args:
            raise ValueError("Invalid saved research context category")
        return value
    if origin is tuple:
        return _decode_collection(args, value, name)
    if kind is EvidenceAttribute:
        return evidence_attributes_from_list([value])[0]
    if isinstance(kind, type) and is_dataclass(kind):
        if not isinstance(value, Mapping) or set(value) != {field.name for field in fields(kind)}:
            raise ValueError("Invalid saved research context fields")
        hints = get_type_hints(kind)
        return kind(**{field: _decode(hint, value[field], field) for field, hint in hints.items()})
    return _decode_scalar(kind, value, name)


def _validate_references(context: ResearchContext) -> None:
    labels = [row.evidence_label for row in context.timeline]
    if len(labels) != len(set(labels)):
        raise ValueError("Duplicate saved research context timeline labels")
    known = set(labels)
    referenced = {row.evidence_label for row in context.identity_candidates} | {
        row.evidence_label for row in context.source_chains
    }
    if not referenced <= known:
        raise ValueError("Unknown saved research context citation")
    for relationship in context.source_relationships:
        left, right = relationship.evidence_labels
        if left not in known or right not in known or left == right:
            raise ValueError("Invalid saved research context relationship citations")


def context_from_dict(data: object) -> ResearchContext | None:
    """Absent metadata stays absent; a saved method version is retained without recomputation."""
    if data is None:
        return None
    context = cast(ResearchContext, _decode(ResearchContext, data))
    _validate_references(context)
    return context


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


def context_to_dict(context: ResearchContext | None) -> dict[str, Any] | None:
    if context is None:
        return None
    data = cast(dict[str, Any], _json_value(asdict(context)))
    context_from_dict(data)
    return data
