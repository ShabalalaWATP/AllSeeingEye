"""JSON-safe provenance records, with no new keys in historical evidence snapshots."""

import json
from collections.abc import Mapping
from dataclasses import asdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from ase.domain.source_dates import SourceDate
from ase.domain.text_transformations import TextTransformation


def provenance_size(
    transformations: tuple[TextTransformation, ...], dates: tuple[SourceDate, ...]
) -> int:

    if not transformations and not dates:
        return 0
    rows = [provenance_to_dict(row) for row in transformations]
    rows.extend(provenance_to_dict(row) for row in dates)
    return 4 * len(json.dumps(rows)) + 256 * len(rows)


def provenance_to_dict(value: SourceDate | TextTransformation) -> dict[str, Any]:
    result = asdict(value)
    for key, item in result.items():
        if isinstance(item, datetime | date):
            result[key] = item.isoformat()
        elif isinstance(item, UUID):
            result[key] = str(item)
    return result


def transformations_from_list(rows: Any) -> tuple[TextTransformation, ...]:
    if not isinstance(rows, list | tuple) or len(rows) > 4:
        raise ValueError("Invalid frozen transformations")
    return tuple(
        TextTransformation(
            **{
                **_base(row),
                "profile_id": UUID(row["profile_id"]) if row.get("profile_id") else None,
            }
        )
        for row in rows
    )


def dates_from_list(rows: Any) -> tuple[SourceDate, ...]:
    if not isinstance(rows, list | tuple) or len(rows) > 4:
        raise ValueError("Invalid frozen source dates")
    result = []
    for row in rows:
        values = _base(row)
        values["value"] = datetime.fromisoformat(row["value"]) if row.get("value") else None
        for field in ("day_start", "day_end"):
            values[field] = date.fromisoformat(row[field]) if row.get(field) else None
        result.append(SourceDate(**values))
    return tuple(result)


def _base(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "limitations": tuple(row.get("limitations", ())),
        "actor_id": UUID(row["actor_id"]) if row.get("actor_id") else None,
    }


def validate_provenance(
    transformations: tuple[TextTransformation, ...], dates: tuple[SourceDate, ...]
) -> None:
    if (
        not isinstance(transformations, tuple)
        or len(transformations) > 4
        or any(not isinstance(row, TextTransformation) for row in transformations)
        or not isinstance(dates, tuple)
        or len(dates) > 4
        or any(not isinstance(row, SourceDate) for row in dates)
    ):
        raise ValueError("Provenance requires at most four immutable transformations and dates")
