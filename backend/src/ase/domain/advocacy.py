"""Devil's advocacy (CIA Tradecraft Primer): a contrarian view of the top judgement.

A second model call attacks the first key judgement. The engine appends the result as a
clearly labelled view and lets it lower that judgement's confidence, never raise it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from typing import Any

from ase.domain.doctrine import Confidence, find_urls
from ase.domain.validation import Finding, Severity

MAX_ARGUMENT_CHARS = 4_000
MAX_RATIONALE_CHARS = 1_200
MAX_LABELS = 20


@dataclass(frozen=True, slots=True)
class DevilsAdvocacy:
    target: str
    argument: str
    evidence: tuple[str, ...] = ()
    lower_confidence: bool = False
    rationale: str = ""
    confidence_before: Confidence | None = None
    confidence_after: Confidence | None = None


ADVOCACY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["argument", "evidence", "lower_confidence", "rationale"],
    "properties": {
        "argument": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "lower_confidence": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
}


class AdvocacyParseError(ValueError):
    """The model's JSON does not fit the advocacy schema; the message names the field."""


def _text(value: object, field_name: str, limit: int) -> str:
    if not isinstance(value, str):
        raise AdvocacyParseError(f"{field_name} must be a string")
    return value.strip()[:limit]


def parse_advocacy(data: Any, target: str) -> DevilsAdvocacy:
    """Turn the model's JSON into a DevilsAdvocacy aimed at the given judgement."""
    if not isinstance(data, dict):
        raise AdvocacyParseError("the advocacy must be a JSON object")
    labels = data.get("evidence") or []
    if not isinstance(labels, list | tuple):
        raise AdvocacyParseError("evidence must be a list")
    argument = _text(data.get("argument", ""), "argument", MAX_ARGUMENT_CHARS)
    if not argument:
        raise AdvocacyParseError("argument must not be empty")
    return DevilsAdvocacy(
        target=target,
        argument=argument,
        evidence=tuple(_text(label, "evidence", 32) for label in labels)[:MAX_LABELS],
        lower_confidence=bool(data.get("lower_confidence", False)),
        rationale=_text(data.get("rationale", ""), "rationale", MAX_RATIONALE_CHARS),
    )


def check_advocacy(
    advocacy: DevilsAdvocacy, known: frozenset[str]
) -> tuple[DevilsAdvocacy | None, tuple[Finding, ...]]:
    """Strip unknown citations; discard the view entirely if it smuggles in a URL."""
    findings: list[Finding] = []
    if find_urls(advocacy.argument) or find_urls(advocacy.rationale):
        findings.append(
            Finding("url", Severity.WARNING, "devils_advocacy", "Discarded: it contained a URL")
        )
        return None, tuple(findings)
    kept = tuple(label for label in advocacy.evidence if label in known)
    findings.extend(
        Finding(
            "citation", Severity.WARNING, "devils_advocacy", f"Unknown evidence {label} removed"
        )
        for label in advocacy.evidence
        if label not in known
    )
    return replace(advocacy, evidence=kept), tuple(findings)


def lowered(confidence: Confidence) -> Confidence:
    """One step down the confidence scale; low stays low."""
    if confidence is Confidence.HIGH:
        return Confidence.MODERATE
    return Confidence.LOW


def advocacy_to_dict(advocacy: DevilsAdvocacy) -> dict[str, Any]:
    data = asdict(advocacy)
    data["confidence_before"] = (
        advocacy.confidence_before.value if advocacy.confidence_before else None
    )
    data["confidence_after"] = (
        advocacy.confidence_after.value if advocacy.confidence_after else None
    )
    return data


def advocacy_from_dict(data: Mapping[str, Any]) -> DevilsAdvocacy:
    parsed = parse_advocacy(dict(data), str(data.get("target", "KJ1")))
    before = data.get("confidence_before")
    after = data.get("confidence_after")
    return replace(
        parsed,
        confidence_before=Confidence(str(before)) if before else None,
        confidence_after=Confidence(str(after)) if after else None,
    )
