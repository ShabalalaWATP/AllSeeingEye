"""Figures and dates in report prose must be traceable to the frozen evidence."""

from datetime import UTC, datetime

from ase.application.reports.numeric_checks import check_figures, evidence_figures
from ase.domain.evidence import EvidenceItem
from ase.domain.report_figures import derivation_of, figures_in
from ase.domain.report_quality_rules import DATE_RULE, FIGURE_RULE
from ase.domain.reports import (
    AssessmentSection,
    Confidence,
    KeyJudgement,
    Probability,
    ReportBody,
    ReportHeader,
    ReportingItem,
    ReportingTheme,
)

PERIOD_FROM = datetime(2026, 9, 1, tzinfo=UTC)
PERIOD_TO = datetime(2026, 9, 14, tzinfo=UTC)


def header() -> ReportHeader:
    return ReportHeader(
        template="intsum",
        title="Test",
        scope={},
        period_from=PERIOD_FROM,
        period_to=PERIOD_TO,
        data_cutoff=PERIOD_TO,
    )


def item(label: str, title: str, summary: str = "") -> EvidenceItem:
    return EvidenceItem(
        label=label,
        event_id=f"ev-{label}",
        source_id="fake_feed",
        source_name="Fake feed",
        independence_key="fake",
        category="news",
        title=title,
        summary=summary or None,
        url=None,
        published_at=datetime(2026, 9, 5, tzinfo=UTC),
        captured_at=datetime(2026, 9, 6, tzinfo=UTC),
        grade="B2",
        reliability="B",
        credibility=2,
        grade_rationale="",
        lon=None,
        lat=None,
        country_iso=None,
        content_hash=f"hash-{label}",
    )


def body_with(*texts: str) -> ReportBody:
    return ReportBody(
        key_judgements=(
            KeyJudgement(
                id="KJ1",
                statement=texts[0],
                probability=Probability.LIKELY,
                confidence=Confidence.MODERATE,
                confidence_statement="Information base: two items.",
                supporting_evidence=("E1",),
            ),
        ),
        reporting=(
            ReportingTheme(
                theme="Activity",
                items=tuple(ReportingItem(text, ("E1",), "B2") for text in texts[1:]),
            ),
        ),
        assessment=(AssessmentSection("Trajectory", "Steady.", ("E1",)),),
        sourcing_statement="One organisation.",
    )


def rules(findings: tuple[object, ...]) -> set[str]:
    return {finding.rule for finding in findings}  # type: ignore[attr-defined]


def test_exact_rounded_and_derived_figures_are_traceable() -> None:
    evidence = (
        item("E1", "2,987 people were displaced from the northern districts on 3 September 2026"),
        item("E2", "A further 1,013 people were displaced from the southern districts"),
    )
    body = body_with(
        "We assess it is likely that about 3,000 people have left the northern districts.",
        "Displacement across both districts reached 4,000 people.",
        "Reporting on 3 September 2026 described the movement.",
    )
    assert check_figures(body, header(), evidence) == ()


def test_invented_figure_and_percentage_point_confusion_are_reported() -> None:
    evidence = (item("E1", "Electricity supply fell by 12% across the region"),)
    body = body_with(
        "We assess it is likely that supply fell by 12 percentage points.",
        "Some 48,000 households were cut off.",
    )
    findings = check_figures(body, header(), evidence)
    messages = " ".join(finding.message for finding in findings)
    assert rules(findings) == {FIGURE_RULE}
    assert "12 percentage points" in messages
    assert "48,000" in messages
    assert all(finding.severity.value == "error" for finding in findings)


def test_ranges_and_source_quoted_wording_are_accepted() -> None:
    evidence = (
        item(
            "E1",
            "The agency reported between 20 and 30 strikes overnight",
            "It said 25 strikes hit the port",
        ),
    )
    body = body_with(
        "We assess it is likely that between 20 and 30 strikes occurred.",
        'The agency said "25 strikes hit the port".',
    )
    assert check_figures(body, header(), evidence) == ()


def test_dates_inside_the_period_pass_and_a_stray_date_is_reported() -> None:
    evidence = (item("E1", "Fighting was reported on 3 September 2026"),)
    body = body_with(
        "We assess it is likely that fighting continues.",
        "Clashes were reported on 3 September 2026 and again on 11 September.",
        "An earlier assault took place on 14 March 2019.",
    )
    findings = check_figures(body, header(), evidence)
    assert rules(findings) == {DATE_RULE}
    assert "14 March 2019" in findings[0].message


def test_durations_enumerations_labels_and_grades_are_not_figures() -> None:
    evidence = (item("E1", "Fighting continued"),)
    body = body_with(
        "We assess it is likely that fighting intensifies over the next two weeks.",
        "Three fronts remain active; see E1 and E12, graded B2 against SIR-2.",
        "The assessment covers the last 14 days.",
    )
    assert check_figures(body, header(), evidence) == ()


def test_currency_amounts_must_match_their_currency() -> None:
    evidence = (item("E1", "The appeal seeks $4 million for the response"),)
    matching = body_with("We assess it is likely that $4 million is needed.")
    mismatched = body_with("We assess it is likely that £4 million is needed.")
    assert check_figures(matching, header(), evidence) == ()
    assert rules(check_figures(mismatched, header(), evidence)) == {FIGURE_RULE}


def test_evidence_dates_and_attribute_figures_are_collected() -> None:
    figures = evidence_figures((item("E1", "Quiet night"),), (PERIOD_FROM.date(), PERIOD_TO.date()))
    assert any(
        row.kind == "date" and row.day == PERIOD_FROM.date().replace(day=5) for row in figures
    )


def test_derivation_names_the_reproducing_sum() -> None:
    known = figures_in("2,987 people and 1,013 people")
    prose = figures_in("4,000 people")[0]
    assert derivation_of(prose, known) == "2987 + 1013"
