"""Two small final-assessment contracts, preserving the historic combined body contract."""

from copy import deepcopy
from typing import Any

from ase.application.reports.sections.contracts import SYNTHESIS_SCHEMA, validate_content
from ase.domain.report_input import _check
from ase.domain.reports import parse_body
from ase.domain.validation import Finding, Severity, _check_judgement

JUDGEMENTS = "synthesis_judgements"
CONTEXT = "synthesis_context"
PARTS = (JUDGEMENTS, CONTEXT)
TITLES = {JUDGEMENTS: "Key judgements", CONTEXT: "Alternatives, warning and collection"}
SCHEMA_NAMES = {JUDGEMENTS: "report_judgements", CONTEXT: "report_context"}


def _subset(names: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(names),
        "properties": {name: deepcopy(SYNTHESIS_SCHEMA["properties"][name]) for name in names},
    }


JUDGEMENTS_SCHEMA = _subset(("key_judgements", "assumptions"))
_judgements = JUDGEMENTS_SCHEMA["properties"]["key_judgements"]
_judgements["maxItems"] = 2
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
JUDGEMENTS_SCHEMA["properties"]["assumptions"]["maxItems"] = 4
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
for _name, _cap in (("alternative_hypotheses", 2), ("gaps", 10), ("collection_recommendations", 4)):
    _context[_name]["maxItems"] = _cap
for _name in ("text", "why_less_likely"):
    _context["alternative_hypotheses"]["items"]["properties"][_name]["maxLength"] = 400
_context["alternative_hypotheses"]["items"]["properties"]["evidence"]["maxItems"] = 8
_context["indicators_and_warning"]["properties"]["changes"]["maxItems"] = 3
_context["indicators_and_warning"]["properties"]["changes"]["items"]["maxLength"] = 240
_context["gaps"]["items"]["properties"]["text"]["maxLength"] = 400
_context["collection_recommendations"]["items"]["maxLength"] = 280
_context["sourcing_statement"]["maxLength"] = 600


def schema_for(part: str, *, remaining_gaps: int = 20) -> dict[str, Any]:
    if part not in PARTS:
        raise ValueError("Unknown synthesis step")
    schema = deepcopy(JUDGEMENTS_SCHEMA if part == JUDGEMENTS else CONTEXT_SCHEMA)
    if part == CONTEXT:
        schema["properties"]["gaps"]["maxItems"] = min(10, max(0, remaining_gaps))
    return schema


def validate_part(
    value: Any,
    *,
    part: str,
    labels: frozenset[str],
    eeis: frozenset[str],
    previous_exists: bool = False,
    remaining_gaps: int = 20,
) -> dict[str, Any]:
    """A reusable partial step has its own exact shape, citations and linked identifiers."""
    _check(value, schema_for(part, remaining_gaps=remaining_gaps), "synthesis_part")
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
