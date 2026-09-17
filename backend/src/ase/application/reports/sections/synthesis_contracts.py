"""Bounded final-assessment contracts, preserving historic combined body identities."""

from copy import deepcopy
from typing import Any

from ase.application.reports.sections.contracts import SYNTHESIS_SCHEMA, validate_content
from ase.application.reports.sections.tier_limits import limits_for
from ase.domain.llm import MAX_OUTPUT_TOKENS
from ase.domain.report_input import _check
from ase.domain.reports import parse_body
from ase.domain.validation import Finding, Severity, _check_judgement

JUDGEMENTS = "synthesis_judgements"
CONTEXT = "synthesis_context"
PARTS = (JUDGEMENTS, CONTEXT)
ALTERNATIVES = "synthesis_alternatives"
COLLECTION = "synthesis_collection"
CONTEXT_PARTS = (ALTERNATIVES, COLLECTION)
ALL_PARTS = (*PARTS, *CONTEXT_PARTS)
TITLES = {
    JUDGEMENTS: "Key judgements",
    CONTEXT: "Alternatives, warning and collection",
    ALTERNATIVES: "Alternatives and warning",
    COLLECTION: "Gaps and collection",
}
SCHEMA_NAMES = {
    JUDGEMENTS: "report_judgements",
    CONTEXT: "report_context",
    ALTERNATIVES: "report_alternatives",
    COLLECTION: "report_collection",
}


def output_limit_for(part: str | None) -> int:
    """Smaller context children retain the operator's lower limit when one is set."""
    return 16_000 if part in CONTEXT_PARTS else MAX_OUTPUT_TOKENS


def _subset(names: tuple[str, ...], source: dict[str, Any] = SYNTHESIS_SCHEMA) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(names),
        "properties": {name: deepcopy(source["properties"][name]) for name in names},
    }


JUDGEMENTS_SCHEMA = _subset(("key_judgements", "assumptions"))
_judgements = JUDGEMENTS_SCHEMA["properties"]["key_judgements"]
_fields = _judgements["items"]["properties"]
_fields["confidence_statement"]["maxLength"] = 600
for _name, _cap in (
    ("supporting_evidence", 8),
    ("contradicting_evidence", 8),
    ("assumptions", 4),
    ("indicators", 2),
):
    _fields[_name]["maxItems"] = _cap
_fields["indicators"]["items"]["maxLength"] = 240
JUDGEMENTS_SCHEMA["properties"]["assumptions"]["items"]["properties"]["text"]["maxLength"] = 400

CONTEXT_SCHEMA = _subset(
    (
        "alternative_hypotheses",
        "indicators_and_warning",
        "gaps",
        "collection_recommendations",
        "sourcing_statement",
    )
)
_context = CONTEXT_SCHEMA["properties"]
for _name, _cap in (("gaps", 10), ("collection_recommendations", 4)):
    _context[_name]["maxItems"] = _cap
for _name in ("text", "why_less_likely"):
    _context["alternative_hypotheses"]["items"]["properties"][_name]["maxLength"] = 400
_context["alternative_hypotheses"]["items"]["properties"]["evidence"]["maxItems"] = 8
_context["indicators_and_warning"]["properties"]["changes"]["maxItems"] = 3
_context["indicators_and_warning"]["properties"]["changes"]["items"]["maxLength"] = 240
_context["gaps"]["items"]["properties"]["text"]["maxLength"] = 400
_context["collection_recommendations"]["items"]["maxLength"] = 280
_context["sourcing_statement"]["maxLength"] = 600
ALTERNATIVES_SCHEMA = _subset(("alternative_hypotheses", "indicators_and_warning"), CONTEXT_SCHEMA)
COLLECTION_SCHEMA = _subset(
    ("gaps", "collection_recommendations", "sourcing_statement"), CONTEXT_SCHEMA
)
_SCHEMAS = {
    JUDGEMENTS: JUDGEMENTS_SCHEMA,
    CONTEXT: CONTEXT_SCHEMA,
    ALTERNATIVES: ALTERNATIVES_SCHEMA,
    COLLECTION: COLLECTION_SCHEMA,
}


def schema_for(
    part: str, *, remaining_gaps: int = 20, research_mode: object = None
) -> dict[str, Any]:
    if part not in ALL_PARTS:
        raise ValueError("Unknown synthesis step")
    schema = deepcopy(_SCHEMAS[part])
    limits = limits_for(research_mode)
    if part == JUDGEMENTS:
        schema["properties"]["key_judgements"]["maxItems"] = limits.judgements
        schema["properties"]["assumptions"]["maxItems"] = limits.assumptions
    if part in (CONTEXT, ALTERNATIVES):
        schema["properties"]["alternative_hypotheses"]["maxItems"] = limits.alternatives
    if part in (CONTEXT, COLLECTION):
        schema["properties"]["gaps"]["maxItems"] = min(10, max(0, remaining_gaps))
    return schema


def validate_aggregate_limits(value: dict[str, Any], *, research_mode: object = None) -> None:
    """A cached combined step must still obey its frozen tier's strict maxima."""
    limits = limits_for(research_mode)
    if (
        len(value["key_judgements"]) > limits.judgements
        or len(value["assumptions"]) > limits.assumptions
        or len(value["alternative_hypotheses"]) > limits.alternatives
    ):
        raise ValueError("Final assessment exceeds the selected depth limits")


def validate_part(
    value: Any,
    *,
    part: str,
    labels: frozenset[str],
    eeis: frozenset[str],
    previous_exists: bool = False,
    remaining_gaps: int = 20,
    research_mode: object = None,
) -> dict[str, Any]:
    """A reusable partial step has its own exact shape, citations and linked identifiers."""
    _check(
        value,
        schema_for(part, remaining_gaps=remaining_gaps, research_mode=research_mode),
        "synthesis_part",
    )
    validate_content(value, labels=labels, eeis=eeis)
    if part == JUDGEMENTS:
        body = parse_body(value)
        for rows in (body.assumptions, body.key_judgements):
            if len({row.id for row in rows}) != len(rows):
                raise ValueError("Synthesis identifiers must be unique")
        findings: list[Finding] = []
        for judgement in body.key_judgements:
            _check_judgement(judgement, frozenset(row.id for row in body.assumptions), findings)
            if previous_exists and judgement.change_from_previous is None:
                raise ValueError("Prior judgements require a declared change")
        if any(row.severity is Severity.ERROR for row in findings):
            raise ValueError("The judgement step does not meet the report rules")
    return deepcopy(value)
