"""The source mix a template expects, checked against the sources a report cites."""

from dataclasses import replace
from datetime import UTC, datetime

from ase.application.reports.source_sufficiency import check_source_sufficiency
from ase.domain.evidence import EvidenceItem
from ase.domain.report_quality_rules import SOURCE_SUFFICIENCY_RULE
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
from ase.domain.source_character import SourceCharacter, characters_of
from ase.domain.source_requirements import assess_source_mix


def item(label: str, source_id: str, organisation: str = "") -> EvidenceItem:
    return EvidenceItem(
        label=label,
        event_id=f"ev-{label}",
        source_id=source_id,
        source_name=source_id,
        independence_key=organisation or source_id,
        category="news",
        title=f"Reporting from {source_id}",
        summary=None,
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


def body(labels: tuple[str, ...], sourcing: str = "Cited sources are listed.") -> ReportBody:
    return ReportBody(
        key_judgements=(
            KeyJudgement(
                id="KJ1",
                statement="We assess it is likely that activity continues.",
                probability=Probability.LIKELY,
                confidence=Confidence.MODERATE,
                confidence_statement="Information base: two items.",
                supporting_evidence=labels,
            ),
        ),
        reporting=(ReportingTheme("Activity", (ReportingItem("Seen.", labels, "B2"),)),),
        assessment=(AssessmentSection("Trajectory", "Steady.", labels),),
        sourcing_statement=sourcing,
    )


def messages(findings: list[object]) -> str:
    return " ".join(finding.message for finding in findings)  # type: ignore[attr-defined]


def test_cyber_summary_needs_a_vendor_advisory_and_a_national_cert() -> None:
    complete = (item("E1", "cyber_unit42"), item("E2", "cyber_cert_ua"))
    assert check_source_sufficiency(body(("E1", "E2")), "cyber_summary", complete) == []
    thin = (item("E1", "cyber_bleeping_computer"), item("E2", "cyber_the_record"))
    findings = check_source_sufficiency(body(("E1", "E2")), "cyber_summary", thin)
    text = messages(findings)
    assert {finding.rule for finding in findings} == {SOURCE_SUFFICIENCY_RULE}
    assert "security vendor or research team advisory" in text
    assert "national CERT" in text
    assert all(finding.severity.value == "error" for finding in findings)


def test_country_brief_needs_an_official_issuer_and_an_independent_outlet() -> None:
    complete = (item("E1", "gov_uk_fcdo_news"), item("E2", "bbc_world"))
    assert check_source_sufficiency(body(("E1", "E2")), "country_brief", complete) == []
    official_only = (item("E1", "gov_uk_fcdo_news"), item("E2", "un_news"))
    findings = check_source_sufficiency(body(("E1", "E2")), "country_brief", official_only)
    assert "independent news outlet" in messages(findings)


def test_intsum_states_how_many_organisations_it_actually_has() -> None:
    two = (item("E1", "bbc_world"), item("E2", "dw_world"))
    findings = check_source_sufficiency(body(("E1", "E2")), "intsum", two)
    assert "at least 3 independent organisations; the report cites 2" in messages(findings)
    three = (*two, item("E3", "france24_en"))
    assert check_source_sufficiency(body(("E1", "E2", "E3")), "intsum", three) == []


def test_a_single_organisation_is_named_and_a_disclosure_lowers_it_to_advisory() -> None:
    alone = (item("E1", "tass_en", "tass"), item("E2", "tass_en", "tass"))
    silent = check_source_sufficiency(body(("E1", "E2")), "intsum", alone)
    assert "comes from one organisation" in messages(silent)
    assert silent[0].severity.value == "error"
    disclosed = check_source_sufficiency(
        body(("E1", "E2"), "All reporting comes from a single organisation."), "intsum", alone
    )
    assert disclosed[0].severity.value == "warning"
    assert "The report says so." in disclosed[0].message


def test_a_disclosed_missing_kind_of_source_is_advisory() -> None:
    thin = (item("E1", "cyber_unit42"), item("E2", "cyber_the_record"))
    disclosed = replace(
        body(("E1", "E2")),
        gaps=(Gap("No national CERT advisory was available in the period."),),
    )
    findings = check_source_sufficiency(disclosed, "cyber_summary", thin)
    assert [finding.severity.value for finding in findings] == ["warning"]


def test_only_cited_sources_count_towards_the_mix() -> None:
    selected = (item("E1", "cyber_unit42"), item("E2", "cyber_cert_ua"))
    findings = check_source_sufficiency(body(("E1",)), "cyber_summary", selected)
    assert "national CERT" in messages(findings)


def test_unlisted_feeds_fall_back_to_their_declared_provenance() -> None:
    unknown = item("E1", "some_new_feed")
    assert characters_of(unknown) == frozenset({SourceCharacter.UNCLASSIFIED})
    instrument = replace(unknown, instrument=True)
    assert characters_of(instrument) == frozenset({SourceCharacter.INSTRUMENT})
    mix = assess_source_mix("aviation_activity", (instrument,))
    assert mix.unmet == () and mix.organisations == 1
