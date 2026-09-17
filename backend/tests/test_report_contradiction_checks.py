"""Disagreement between cited sources is named, not only counted."""

from datetime import UTC, datetime

from ase.application.reports.contradiction_checks import check_contradictions
from ase.domain.evidence import EvidenceItem
from ase.domain.judgement_assessment import build_report_assessment
from ase.domain.report_quality_rules import CONTRADICTION_RULE
from ase.domain.reports import (
    AssessmentSection,
    Confidence,
    KeyJudgement,
    Probability,
    ReportBody,
    ReportingItem,
    ReportingTheme,
)


def item(label: str, source_id: str, name: str, reliability: str, credibility: int) -> EvidenceItem:
    return EvidenceItem(
        label=label,
        event_id=f"ev-{label}",
        source_id=source_id,
        source_name=name,
        independence_key=source_id,
        category="conflict",
        title=f"{name} reports on the crossing",
        summary=None,
        url=None,
        published_at=datetime(2026, 9, 5, tzinfo=UTC),
        captured_at=datetime(2026, 9, 6, tzinfo=UTC),
        grade=f"{reliability}{credibility}",
        reliability=reliability,
        credibility=credibility,
        grade_rationale="",
        lon=None,
        lat=None,
        country_iso=None,
        content_hash=f"hash-{label}",
    )


SUPPORT = item("E1", "bbc_world", "BBC World", "B", 2)
AGAINST = item("E2", "tass_en", "TASS", "B", 2)
WEAK = item("E3", "gdelt_news", "GDELT", "D", 4)


def body(contradicting: tuple[str, ...]) -> ReportBody:
    return ReportBody(
        key_judgements=(
            KeyJudgement(
                id="KJ1",
                statement="We assess it is likely that the crossing has closed.",
                probability=Probability.LIKELY,
                confidence=Confidence.MODERATE,
                confidence_statement="Information base: two items.",
                supporting_evidence=("E1",),
                contradicting_evidence=contradicting,
            ),
        ),
        reporting=(ReportingTheme("Crossing", (ReportingItem("Closed.", ("E1",), "B2"),)),),
        assessment=(AssessmentSection("Trajectory", "Steady.", ("E1",)),),
        sourcing_statement="Two organisations.",
    )


def check(contradicting: tuple[str, ...], evidence: tuple[EvidenceItem, ...]) -> list[object]:
    report = body(contradicting)
    assessment = build_report_assessment(report, evidence, ())
    return check_contradictions(report, assessment, evidence)  # type: ignore[return-value]


def test_equal_strength_disagreement_names_both_sides_and_gates() -> None:
    findings = check(("E2",), (SUPPORT, AGAINST))
    assert len(findings) == 1
    finding = findings[0]
    assert (finding.rule, finding.location, finding.severity.value) == (
        CONTRADICTION_RULE,
        "KJ1",
        "error",
    )
    for expected in (
        "the crossing has closed",
        "E1 (BBC World, graded B2, an independent news outlet)",
        "E2 (TASS, graded B2, a state-aligned outlet)",
        "at least as strong",
        "not independently verified",
    ):
        assert expected in finding.message


def test_weaker_opposition_is_surfaced_without_gating() -> None:
    findings = check(("E3",), (SUPPORT, WEAK))
    assert [finding.severity.value for finding in findings] == ["warning"]
    assert "weaker than the support" in findings[0].message


def test_a_judgement_with_no_opposition_produces_nothing() -> None:
    assert check((), (SUPPORT,)) == []


def test_an_absent_assessment_degrades_quietly() -> None:
    assert check_contradictions(body(("E2",)), None, (SUPPORT, AGAINST)) == []
