"""Every PIR, SIR and EEI is answered, disclosed as a gap, or named as uncovered."""

from dataclasses import replace

from ase.application.reports.requirement_gate import check_requirement_gate, requirement_rows
from ase.domain.direction import Direction
from ase.domain.report_quality_rules import REQUIREMENT_COVERAGE_RULE, REQUIREMENT_GATE_RULE
from ase.domain.reports import (
    AssessmentSection,
    Confidence,
    Gap,
    KeyJudgement,
    Probability,
    ReportBody,
    ReportingItem,
    ReportingTheme,
)
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.validation_types import Finding, Severity

DIRECTION = Direction(
    pir="Will fighting around Kharkiv intensify this week?",
    sirs=("Which reinforcement columns are moving towards Kharkiv?", "Has strike tempo risen?"),
    eeis=("Are reinforcements moving north?",),
)


def body(*, reporting: tuple[ReportingTheme, ...] = (), gaps: tuple[Gap, ...] = ()) -> ReportBody:
    return ReportBody(
        key_judgements=(
            KeyJudgement(
                id="KJ1",
                statement="We assess it is likely that fighting around Kharkiv intensifies.",
                probability=Probability.LIKELY,
                confidence=Confidence.MODERATE,
                confidence_statement="Information base: two items.",
                supporting_evidence=("E1",),
            ),
        ),
        reporting=reporting,
        assessment=(AssessmentSection("Trajectory", "Steady.", ("E1",)),),
        gaps=gaps,
        sourcing_statement="Two organisations.",
    )


def locations(findings: list[Finding]) -> list[str]:
    return [finding.location for finding in findings]


def test_unanswered_requirements_are_named_with_their_question() -> None:
    findings = check_requirement_gate(body(), DIRECTION)
    assert locations(findings) == ["SIR-1", "SIR-2", "EEI-1"]
    assert {finding.rule for finding in findings} == {REQUIREMENT_GATE_RULE}
    assert all(finding.severity is Severity.ERROR for finding in findings)
    assert "Which reinforcement columns are moving towards Kharkiv?" in findings[0].message


def test_the_pir_counts_as_answered_when_a_judgement_carries_support() -> None:
    assert "PIR-1" not in locations(check_requirement_gate(body(), DIRECTION))
    elsewhere = replace(
        body(),
        key_judgements=(
            replace(
                body().key_judgements[0],
                statement="We assess it is likely that harbour traffic recovers.",
                supporting_evidence=(),
            ),
        ),
    )
    assert "PIR-1" in locations(check_requirement_gate(elsewhere, DIRECTION))


def test_a_requirement_named_in_a_heading_with_evidence_is_covered() -> None:
    named = body(
        reporting=(
            ReportingTheme(
                "SIR-1 reinforcements", (ReportingItem("Columns seen.", ("E1",), "B2"),)
            ),
        )
    )
    assert "SIR-1" not in locations(check_requirement_gate(named, DIRECTION))


def test_prose_that_addresses_the_question_counts_as_answered() -> None:
    covered = body(
        reporting=(
            ReportingTheme(
                "Tempo",
                (ReportingItem("Strike tempo has risen sharply this week.", ("E1",), "B2"),),
            ),
        )
    )
    assert "SIR-2" not in locations(check_requirement_gate(covered, DIRECTION))


def test_a_disclosed_gap_is_not_reported_again() -> None:
    disclosed = body(gaps=(Gap("No reporting on the eastern road.", "EEI-1"),))
    assert "EEI-1" not in locations(check_requirement_gate(disclosed, DIRECTION))


def test_the_section_pipeline_finding_is_not_duplicated() -> None:
    existing = (
        Finding(REQUIREMENT_COVERAGE_RULE, Severity.ERROR, "EEI-1", "Not separately assessed."),
    )
    assert "EEI-1" not in locations(check_requirement_gate(body(), DIRECTION, (), existing))


def test_authored_requirements_replace_the_direction_identifiers() -> None:
    authored = (
        IntelligenceRequirement(
            id="IR-1", question="What is the state of the northern road?", required=True, priority=1
        ),
    )
    assert requirement_rows(DIRECTION, authored) == (
        ("IR-1", "What is the state of the northern road?"),
    )
    assert locations(check_requirement_gate(body(), DIRECTION, authored)) == ["IR-1"]


def test_no_direction_means_no_requirement_gate() -> None:
    assert check_requirement_gate(body(), None) == []
