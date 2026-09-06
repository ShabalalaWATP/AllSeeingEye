"""Keep bounded event metadata as valid JSON, with explicit omitted-item counts."""

import json
from typing import Any

from ase.domain.events import MAX_ATTRIBUTE_CHARS


def bounded_json(values: list[Any]) -> tuple[str, int]:
    retained: list[Any] = []
    for value in values:
        candidate = json.dumps([*retained, value], ensure_ascii=False, separators=(",", ":"))
        if len(candidate) > MAX_ATTRIBUTE_CHARS:
            break
        retained.append(value)
    return json.dumps(retained, ensure_ascii=False, separators=(",", ":")), len(values) - len(
        retained
    )
