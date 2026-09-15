"""Narrow wire schemas and citation checks before a step becomes reusable."""

import html
import json
import re
from copy import deepcopy
from typing import Any

from ase.domain.doctrine import scan_likelihood
from ase.domain.report_input import _check
from ase.domain.report_schema import REPORT_BODY_SCHEMA

MAX_RESPONSE_BYTES = 128 * 1024
_HTML = re.compile(r"<\s*(?:/?[a-z][\w:-]*\b|!|\?)", re.IGNORECASE)
_LINK = re.compile(
    r"[a-z][a-z0-9+.-]*://|\b(?:javascript:|data:|mailto:|file:)"
    r"|\[[^\]]*\]\([^)]*\)|(?<!:)//[a-z0-9]",
    re.IGNORECASE,
)
_FIELDS = REPORT_BODY_SCHEMA["properties"]


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


TOPIC_SCHEMA = _object(
    {
        "reporting": {
            "type": "array",
            "maxItems": 4,
            "items": deepcopy(_FIELDS["reporting"]["items"]["properties"]["items"]["items"]),
        },
        "assessment": {**deepcopy(_FIELDS["assessment"]), "minItems": 0, "maxItems": 1},
        "gaps": {**deepcopy(_FIELDS["gaps"]), "maxItems": 1},
    }
)
TOPIC_SCHEMA["properties"]["assessment"]["items"]["properties"]["text"]["maxLength"] = 1600
SYNTHESIS_SCHEMA = _object(
    {
        key: deepcopy(_FIELDS[key])
        for key in (
            "key_judgements",
            "assumptions",
            "alternative_hypotheses",
            "indicators_and_warning",
            "gaps",
            "collection_recommendations",
            "sourcing_statement",
        )
    }
)
for _name, _cap in (
    ("key_judgements", 8),
    ("assumptions", 8),
    ("alternative_hypotheses", 4),
    ("gaps", 20),
    ("collection_recommendations", 8),
):
    SYNTHESIS_SCHEMA["properties"][_name]["maxItems"] = _cap


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("Duplicate JSON property")
        value[key] = child
    return value


def _constant(_value: str) -> None:
    raise ValueError("Non-finite JSON number")


def decode(content: str) -> Any:
    if len(content.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ValueError("Section output exceeds its size limit")
    return json.loads(content, object_pairs_hook=_unique, parse_constant=_constant)


def validate_step(
    value: Any,
    *,
    synthesis: bool,
    labels: frozenset[str],
    eeis: frozenset[str],
) -> dict[str, Any]:
    # Reuse the strict new-report wire checker, never the tolerant historic decoder.
    _check(value, SYNTHESIS_SCHEMA if synthesis else TOPIC_SCHEMA, "section")

    validate_content(value, labels=labels, eeis=eeis)
    if not synthesis:
        if not any(value.values()):
            raise ValueError("A topic must contain reporting, assessment or a gap")
        for row in value["reporting"]:
            scan = scan_likelihood(row["text"])
            if scan.bands or scan.forbidden:
                raise ValueError("Reporting must not use likelihood judgements")
    return deepcopy(value)


def validate_content(value: Any, *, labels: frozenset[str], eeis: frozenset[str]) -> None:
    """Shared untrusted-text and exact-reference rules after the step's strict schema check."""

    def walk(item: Any, key: str = "") -> None:
        if isinstance(item, dict):
            for name, child in item.items():
                walk(child, name)
        elif isinstance(item, list):
            if key in {"evidence", "supporting_evidence", "contradicting_evidence"}:
                if len(set(item)) != len(item) or any(label not in labels for label in item):
                    raise ValueError("Citations must identify supplied frozen evidence")
            else:
                for child in item:
                    walk(child)
        elif isinstance(item, str):
            text = html.unescape(html.unescape(item))
            if (
                _LINK.search(text)
                or _HTML.search(text)
                or any(ord(c) < 32 and c not in "\n\t" for c in item)
            ):
                raise ValueError("Section text must not contain links, HTML or controls")
            if key == "eei" and item not in eeis:
                raise ValueError("Gap references an unknown requirement")

    walk(value)
