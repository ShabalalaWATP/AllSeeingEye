"""Run the mechanical post-draft checks over a finished body and collect their findings.

Every check here is deterministic and free: it reads the drafted report and the frozen
evidence and returns findings. None of them rewrites the report, and an input a check
cannot handle produces no finding rather than a failure.
"""

from __future__ import annotations

from collections.abc import Sequence

from ase.application.reports.numeric_checks import check_figures
from ase.application.reports.style_checks import check_house_style, check_structure
from ase.application.reports.templates import Template
from ase.domain.evidence import EvidenceItem
from ase.domain.reports import ReportBody, ReportHeader
from ase.domain.validation_types import Finding


def mechanical_quality_findings(
    body: ReportBody,
    header: ReportHeader,
    template: Template,
    evidence: Sequence[EvidenceItem],
) -> tuple[Finding, ...]:
    """Cheapest first: figure and date traceability, then structure and style."""
    return (
        *check_figures(body, header, evidence),
        *check_structure(body, template.id),
        *check_house_style(body),
    )
