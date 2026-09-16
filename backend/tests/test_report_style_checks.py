"""House style and template structure are reported, never silently rewritten."""

from dataclasses import replace

from ase.application.reports.style_checks import check_house_style, check_structure
from ase.domain.house_style import style_violations
from ase.domain.report_quality_rules import HOUSE_STYLE_RULE, TEMPLATE_STRUCTURE_RULE
from ase.domain.report_structure import structure_for
from ase.domain.reports import (
    AssessmentSection,
    Confidence,
    Gap,
    IndicatorsAndWarning,
    KeyJudgement,
    Probability,
    ReportBody,
    ReportingItem,
    ReportingTheme,
)


def judgement(index: int, statement: str = "") -> KeyJudgement:
    return KeyJudgement(
        id=f"KJ{index}",
        statement=statement or f"We assess it is likely that position {index} holds.",
        probability=Probability.LIKELY,
        confidence=Confidence.MODERATE,
        confidence_statement="Information base: two items.",
        supporting_evidence=("E1",),
    )


def theme(name: str, text: str = "Reported activity continued overnight.") -> ReportingTheme:
    return ReportingTheme(theme=name, items=(ReportingItem(text, ("E1",), "B2"),))


def intsum_body(**overrides: object) -> ReportBody:
    base = ReportBody(
        key_judgements=(judgement(1), judgement(2), judgement(3)),
        reporting=(theme("Ground activity", "A" * 400), theme("Air activity", "B" * 400)),
        assessment=(AssessmentSection("Trajectory", "C" * 400, ("E1",)),),
        indicators_and_warning=IndicatorsAndWarning(changes=("More hotspots to the north",)),
        gaps=(Gap("No reporting on the eastern road."),),
        collection_recommendations=("Task a review of the northern approaches.",),
        sourcing_statement="Three items from two independent organisations.",
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def messages(findings: list[object]) -> str:
    return " ".join(finding.message for finding in findings)  # type: ignore[attr-defined]


def test_a_conforming_intsum_raises_no_structure_or_style_finding() -> None:
    body = intsum_body()
    assert check_structure(body, "intsum") == []
    assert check_house_style(body) == []


def test_missing_parts_and_judgement_count_are_reported() -> None:
    body = intsum_body(key_judgements=(judgement(1),), collection_recommendations=())
    findings = check_structure(body, "intsum")
    assert {finding.rule for finding in findings} == {TEMPLATE_STRUCTURE_RULE}
    assert "collection recommendations" in messages(findings)
    assert "between 3 and 5 key judgements" in messages(findings)


def test_expected_cyber_headings_must_be_present_and_in_order() -> None:
    ordered = intsum_body(
        reporting=(
            theme("New known exploited vulnerabilities"),
            theme("Ransomware activity"),
            theme("Outages and shutdowns"),
        ),
        key_judgements=(judgement(1),),
    )
    assert check_structure(ordered, "cyber_summary") == []
    swapped = replace(ordered, reporting=tuple(reversed(ordered.reporting)))
    findings = check_structure(swapped, "cyber_summary")
    assert "not in the order" in messages(findings)
    missing = replace(ordered, reporting=ordered.reporting[:2])
    assert "Outages and shutdowns" in messages(check_structure(missing, "cyber_summary"))


def test_an_empty_heading_is_reported() -> None:
    body = intsum_body(reporting=(theme(""), theme("Air activity")))
    assert "without a heading" in messages(check_structure(body, "intsum"))


def test_length_bounds_use_the_template_row() -> None:
    long_body = intsum_body(assessment=(AssessmentSection("Trajectory", "C" * 30_000, ("E1",)),))
    assert "beyond the 24,000" in messages(check_structure(long_body, "intsum"))
    short_body = intsum_body(
        reporting=(theme("Ground activity", "Short."),),
        assessment=(AssessmentSection("Trajectory", "Short.", ("E1",)),),
    )
    assert "below the 600" in messages(check_structure(short_body, "intsum"))


def test_american_spelling_em_dash_markup_and_inline_citations_are_named() -> None:
    body = intsum_body(
        key_judgements=(
            judgement(1, "We assess the defense organization will mobilize — quickly."),
            judgement(2, "We assess **bold** claims rest on [E1] alone."),
            judgement(3),
        )
    )
    findings = check_house_style(body)
    assert {finding.rule for finding in findings} == {HOUSE_STYLE_RULE}
    text = messages(findings)
    for expected in ("defence", "organisation", "mobilise", "dash", "Markdown emphasis", "[E1]"):
        assert expected in text
    assert body == intsum_body(key_judgements=body.key_judgements)


def test_html_and_entities_in_a_structured_field_are_reported() -> None:
    body = intsum_body(gaps=(Gap("No reporting <b>yet</b> on the road."),))
    assert "HTML tag" in messages(check_house_style(body))
    entity = intsum_body(gaps=(Gap("No reporting&nbsp;yet on the road."),))
    assert "HTML entity" in messages(check_house_style(entity))


def test_style_violations_name_the_expected_form() -> None:
    violations = style_violations("The center analyzed the color of the harbor.")
    assert [row.expected for row in violations] == ["centre", "analysed", "colour", "harbour"]


def test_an_unknown_template_keeps_the_shared_minimum() -> None:
    structure = structure_for("not_a_template")
    assert structure.required_parts == ("key_judgements", "reporting", "sourcing_statement")
    assert check_structure(intsum_body(), "not_a_template") == []
