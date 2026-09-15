"""Canonical JSON bridge for immutable Research Brief revisions."""

from __future__ import annotations

import json
from typing import Any, cast

from pydantic import TypeAdapter, ValidationError

from ase.domain.research_brief import MAX_BRIEF_BYTES, ResearchBrief
from ase.domain.research_brief_values import BriefValidationError

_BRIEF = TypeAdapter(ResearchBrief)


def brief_to_dict(brief: ResearchBrief) -> dict[str, Any]:
    if not isinstance(brief, ResearchBrief):
        raise BriefValidationError("brief", "Use a validated Research Brief")
    value = _BRIEF.dump_python(brief, mode="json")
    if not isinstance(value, dict):
        raise BriefValidationError("brief", "Invalid Research Brief encoding")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise BriefValidationError("brief", "Research Brief cannot be safely encoded") from exc
    if len(encoded.encode("utf-8")) > MAX_BRIEF_BYTES:
        raise BriefValidationError("brief", "Research Brief exceeds its checkpoint size budget")
    return cast(dict[str, Any], json.loads(encoded))


def brief_from_dict(value: dict[str, Any]) -> ResearchBrief:
    """Reject unknown, coerced or lossy fields rather than silently changing a saved revision."""
    if type(value) is not dict:
        raise BriefValidationError("brief", "Research Brief must be an object")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
        if len(encoded.encode("utf-8")) > MAX_BRIEF_BYTES:
            raise BriefValidationError("brief", "Research Brief exceeds its checkpoint size budget")
        brief = _BRIEF.validate_python(value)
    except BriefValidationError:
        raise
    except ValidationError as exc:
        error = exc.errors(include_input=False)[0]
        location = error.get("loc", ())
        nested = error.get("ctx", {}).get("error")
        if isinstance(nested, BriefValidationError):
            field = nested.field
            section = str(location[0]) if location else ""
            if section and field != section and not field.startswith(f"{section}."):
                field = f"{section}.{field}"
        else:
            field = ".".join(map(str, location)) or "brief"
        raise BriefValidationError(field, "Invalid saved Research Brief") from exc
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise BriefValidationError("brief", "Invalid saved Research Brief") from exc
    canonical = json.dumps(
        brief_to_dict(brief), ensure_ascii=False, allow_nan=False, sort_keys=True
    )
    if canonical != encoded:
        raise BriefValidationError("brief", "Research Brief must use its canonical schema")
    return brief
