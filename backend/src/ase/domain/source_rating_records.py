"""Strict bounded JSON conversion of frozen source ratings; no retrospective lookup."""

from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Any, cast, get_args

from ase.domain.events import Reliability
from ase.domain.source_rating_catalog import ProvenanceRole
from ase.domain.source_ratings import SourceRating

MAX_RATING_TEXT = 1_200
MAX_RATING_LIMITATIONS = 16
RATING_FIELDS = frozenset(
    {
        "policy_version",
        "status",
        "assessed_grade",
        "basis",
        "scope",
        "limitations",
        "provenance_role",
        "publisher_reliability_assessed",
        "reviewed_at",
    }
)


def _text(value: object, name: str, limit: int = MAX_RATING_TEXT) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Source rating {name} must be nonempty text within {limit} characters")
    return value


def source_rating_from_dict(data: object) -> SourceRating | None:
    """Missing legacy metadata stays unknown; malformed new metadata is never coerced."""
    if data is None:
        return None
    if not isinstance(data, Mapping) or set(data) != RATING_FIELDS:
        raise ValueError("Source rating fields do not match the frozen metadata contract")
    version = _text(data["policy_version"], "policy_version", 64)
    status = data["status"]
    if status not in ("editorial", "unassessed"):
        raise ValueError("Source rating status is invalid")
    raw_grade = data["assessed_grade"]
    if raw_grade is not None and (
        not isinstance(raw_grade, str) or raw_grade not in tuple(Reliability)
    ):
        raise ValueError("Source rating assessed_grade is invalid")
    grade = Reliability(raw_grade) if raw_grade is not None else None
    basis, scope = _text(data["basis"], "basis"), _text(data["scope"], "scope")
    raw_limits = data["limitations"]
    if not isinstance(raw_limits, list) or not 1 <= len(raw_limits) <= MAX_RATING_LIMITATIONS:
        raise ValueError("Source rating limitations must be a bounded nonempty list")
    limits = tuple(_text(value, "limitation") for value in raw_limits)
    role = data["provenance_role"]
    if role not in get_args(ProvenanceRole):
        raise ValueError("Source rating provenance_role is invalid")
    assessed = data["publisher_reliability_assessed"]
    if type(assessed) is not bool:
        raise ValueError("Source rating publisher_reliability_assessed must be a boolean")
    if (status == "unassessed" and (grade is not None or assessed)) or (
        status == "editorial" and grade is None
    ):
        raise ValueError("Source rating assessment status and grade are inconsistent")
    if assessed and role in ("aggregator", "platform", "unassessed"):
        raise ValueError("A platform or aggregator cannot confer publisher reliability")
    reviewed = data["reviewed_at"]
    timestamp = None
    if reviewed is not None:
        timestamp = datetime.fromisoformat(_text(reviewed, "reviewed_at", 64))
        if timestamp.utcoffset() is None:
            raise ValueError("Source rating reviewed_at must include a timezone")
    return SourceRating(
        policy_version=version,
        status=status,
        assessed_grade=grade,
        basis=basis,
        scope=scope,
        limitations=limits,
        provenance_role=cast(ProvenanceRole, role),
        publisher_reliability_assessed=assessed,
        reviewed_at=timestamp,
    )


def source_rating_to_dict(rating: SourceRating | None) -> dict[str, Any] | None:
    if rating is None:
        return None
    data = asdict(rating)
    data["assessed_grade"] = rating.assessed_grade.value if rating.assessed_grade else None
    data["limitations"] = list(rating.limitations)
    data["reviewed_at"] = rating.reviewed_at.isoformat() if rating.reviewed_at else None
    source_rating_from_dict(data)
    return data
