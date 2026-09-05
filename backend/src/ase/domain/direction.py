"""Direction for a free-form ask (docs/03 section 8): the question as PIR, SIRs and EEIs.

The direction call turns a question into the requirement structure the doctrine uses,
plus search terms that steer evidence selection. The engine keeps the result beside the
report version so the reader can see what the answer was asked to cover.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from ase.domain.events import Category

MAX_SIRS = 6
MAX_EEIS = 10
MAX_TERMS = 12
MAX_TEXT_CHARS = 300
MAX_TERM_CHARS = 60


@dataclass(frozen=True, slots=True)
class Direction:
    pir: str
    sirs: tuple[str, ...] = ()
    eeis: tuple[str, ...] = ()
    search_terms: tuple[str, ...] = ()
    categories: tuple[Category, ...] = ()

    def requirement_ids(self) -> tuple[str, ...]:
        return (
            "PIR-1",
            *(f"SIR-{index}" for index in range(1, len(self.sirs) + 1)),
            *(f"EEI-{index}" for index in range(1, len(self.eeis) + 1)),
        )

    def lines(self) -> list[str]:
        """The requirements as 'id: text' lines, for prompts and the rendered report."""
        lines = [f"PIR-1: {self.pir}"]
        lines.extend(f"SIR-{index}: {text}" for index, text in enumerate(self.sirs, 1))
        lines.extend(f"EEI-{index}: {text}" for index, text in enumerate(self.eeis, 1))
        return lines


DIRECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["pir", "sirs", "eeis", "search_terms", "categories"],
    "properties": {
        "pir": {"type": "string"},
        "sirs": {"type": "array", "items": {"type": "string"}},
        "eeis": {"type": "array", "items": {"type": "string"}},
        "search_terms": {"type": "array", "items": {"type": "string"}},
        "categories": {
            "type": "array",
            "items": {"type": "string", "enum": [category.value for category in Category]},
        },
    },
}


class DirectionParseError(ValueError):
    """The model's JSON does not fit the direction schema; the message names the field."""


def _texts(value: object, field_name: str, limit: int, each: int) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise DirectionParseError(f"{field_name} must be a list")
    kept: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise DirectionParseError(f"{field_name} must contain strings")
        text = " ".join(item.split())[:each]
        if text and text not in kept:
            kept.append(text)
    return tuple(kept[:limit])


def _categories(value: object) -> tuple[Category, ...]:
    if not isinstance(value, list | tuple):
        return ()
    found: list[Category] = []
    for item in value:
        try:
            category = Category(str(item).strip().lower())
        except ValueError:
            continue
        if category not in found:
            found.append(category)
    return tuple(found)


def parse_direction(data: Any) -> Direction:
    """Turn the model's JSON into a Direction, bounding lengths and dropping unknown fields."""
    if not isinstance(data, dict):
        raise DirectionParseError("the direction must be a JSON object")
    pir = data.get("pir")
    if not isinstance(pir, str) or not pir.strip():
        raise DirectionParseError("pir must be a non-empty string")
    return Direction(
        pir=" ".join(pir.split())[:MAX_TEXT_CHARS],
        sirs=_texts(data.get("sirs"), "sirs", MAX_SIRS, MAX_TEXT_CHARS),
        eeis=_texts(data.get("eeis"), "eeis", MAX_EEIS, MAX_TEXT_CHARS),
        search_terms=_texts(data.get("search_terms"), "search_terms", MAX_TERMS, MAX_TERM_CHARS),
        categories=_categories(data.get("categories")),
    )


def direction_to_dict(direction: Direction) -> dict[str, Any]:
    data = asdict(direction)
    data["categories"] = [category.value for category in direction.categories]
    return data


def direction_from_dict(data: Mapping[str, Any]) -> Direction:
    return parse_direction(dict(data))
