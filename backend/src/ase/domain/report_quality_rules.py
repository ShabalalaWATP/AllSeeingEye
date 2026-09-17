"""Names of the post-draft quality rules whose findings are shown as review reasons.

Each rule is mechanical unless noted. A rule never rewrites the report: it produces a
finding, and the quality gate turns an error-severity finding into a visible reason on
the report's status.
"""

from __future__ import annotations

FIGURE_RULE = "figure_consistency"
DATE_RULE = "date_consistency"
HOUSE_STYLE_RULE = "house_style"
TEMPLATE_STRUCTURE_RULE = "template_structure"
SOURCE_SUFFICIENCY_RULE = "source_sufficiency"
REQUIREMENT_GATE_RULE = "requirement_gate"
CONTRADICTION_RULE = "contradiction"
# The only rule that consults a model; it is skipped when none is available.
ENTAILMENT_RULE = "entailment"
# Raised by the section pipeline before this gate runs.
REQUIREMENT_COVERAGE_RULE = "requirement_coverage"

REVIEW_RULES = frozenset(
    {
        FIGURE_RULE,
        DATE_RULE,
        HOUSE_STYLE_RULE,
        TEMPLATE_STRUCTURE_RULE,
        SOURCE_SUFFICIENCY_RULE,
        REQUIREMENT_GATE_RULE,
        REQUIREMENT_COVERAGE_RULE,
        CONTRADICTION_RULE,
        ENTAILMENT_RULE,
    }
)

MAX_REVIEW_REASONS = 40
