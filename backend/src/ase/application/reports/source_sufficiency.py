"""Check the mix of sources a report actually cites against its template's expectations.

Mechanical, with no model call. Where the mix is not met, the gap is stated plainly on
the report rather than left to look like balance the sourcing does not have. A report
whose sourcing statement already discloses the gap keeps the note as an advisory one.
"""

from __future__ import annotations

from collections.abc import Sequence

from ase.domain.evidence import EvidenceItem
from ase.domain.report_quality_rules import SOURCE_SUFFICIENCY_RULE
from ase.domain.reports import ReportBody
from ase.domain.source_requirements import assess_source_mix
from ase.domain.validation_types import Finding, Severity

SINGLE_ORGANISATION_CUES = (
    "single organisation",
    "one organisation",
    "a single source",
    "one source",
    "single reporting line",
    "one reporting line",
)


def _disclosed(body: ReportBody, cues: Sequence[str]) -> bool:
    text = " ".join([body.sourcing_statement, *(gap.text for gap in body.gaps)]).casefold()
    return any(cue in text for cue in cues)


def _severity(disclosed: bool) -> Severity:
    return Severity.WARNING if disclosed else Severity.ERROR


def check_source_sufficiency(
    body: ReportBody, template_id: str, evidence: Sequence[EvidenceItem]
) -> list[Finding]:
    """Report every expectation of the template's source mix the citations do not meet."""
    labels = body.cited_labels()
    cited = [item for item in evidence if item.label in labels]
    if not cited:
        return []
    mix = assess_source_mix(template_id, cited)
    findings: list[Finding] = []
    for requirement in mix.unmet:
        disclosed = _disclosed(body, requirement.gap_cues)
        stated = " The report's sourcing statement discloses this." if disclosed else ""
        findings.append(
            Finding(
                SOURCE_SUFFICIENCY_RULE,
                _severity(disclosed),
                "sourcing_statement",
                f"The {template_id} template expects {requirement.description}, and none of "
                f"the cited sources is one.{stated}",
            )
        )
    if mix.single_organisation:
        disclosed = _disclosed(body, SINGLE_ORGANISATION_CUES)
        stated = " The report says so." if disclosed else ""
        findings.append(
            Finding(
                SOURCE_SUFFICIENCY_RULE,
                _severity(disclosed),
                "sourcing_statement",
                "Every cited source in this report comes from one organisation, so the "
                f"reporting is not corroborated.{stated}",
            )
        )
    elif mix.organisations < mix.minimum_organisations:
        findings.append(
            Finding(
                SOURCE_SUFFICIENCY_RULE,
                Severity.ERROR,
                "sourcing_statement",
                f"The {template_id} template expects at least "
                f"{mix.minimum_organisations} independent organisations; the report cites "
                f"{mix.organisations}.",
            )
        )
    return findings
