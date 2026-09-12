"""Requirement coverage remains honest and repeated model gaps stay concise."""

from ase.application.reports.sections.quality import ensure_requirement_coverage
from ase.domain.direction import Direction
from ase.domain.reports import (
    AssessmentSection,
    Gap,
    ReportBody,
    ReportingItem,
    ReportingTheme,
)


def test_unanswered_eeis_add_neutral_notices_and_require_review():
    direction = Direction(
        "What does the packet establish?",
        eeis=("What was reported?", "Was it independently verified?", "What remains unknown?"),
    )
    repeated = "Independent verification was not established from the retained source material."
    body = ReportBody(
        reporting=(ReportingTheme("EEI-1: reporting", (ReportingItem("A report.", ("E1",)),)),),
        assessment=(AssessmentSection("EEI-1: assessment", "Limited assessment.", ("E1",)),),
        gaps=(
            Gap(repeated, "EEI-2"),
            Gap(repeated + " Additional collection is required.", "EEI-2"),
        ),
    )

    completed, findings = ensure_requirement_coverage(body, direction)

    assert [gap.eei for gap in completed.gaps] == ["EEI-2", "EEI-3"]
    assert completed.gaps[1].text == (
        "Not separately assessed from the retained evidence: What remains unknown?"
    )
    assert [finding.location for finding in findings] == ["EEI-2", "EEI-3"]
    assert all(finding.rule == "requirement_coverage" for finding in findings)
    assert "did not occur" not in " ".join(gap.text for gap in completed.gaps).casefold()


def test_explicit_topic_support_is_not_overridden_by_a_partial_gap():
    direction = Direction("Question", eeis=("Requirement one",))
    body = ReportBody(gaps=(Gap("One source limitation remains.", "EEI-1"),))

    completed, findings = ensure_requirement_coverage(
        body,
        direction,
        supported=frozenset({"EEI-1"}),
    )

    assert completed.gaps == body.gaps
    assert findings == ()


def test_gap_deduplication_keeps_the_complete_version():
    incomplete = "Independent verification remains unresolved because retained source material"
    complete = incomplete + " does not identify an original witness."
    body = ReportBody(gaps=(Gap(incomplete), Gap(complete)))

    cleaned, _ = ensure_requirement_coverage(body, None)

    assert cleaned.gaps == (Gap(complete),)


def test_unanswered_requirement_notice_survives_the_twenty_gap_cap():
    direction = Direction("Question", eeis=("Supported requirement", "Missing requirement"))
    existing = tuple(Gap(f"{index} {chr(65 + index) * 70}.", "EEI-1") for index in range(20))

    completed, findings = ensure_requirement_coverage(
        ReportBody(gaps=existing),
        direction,
        supported=frozenset({"EEI-1"}),
    )

    assert len(completed.gaps) == 20
    assert completed.gaps[0] == Gap(
        "Not separately assessed from the retained evidence: Missing requirement",
        "EEI-2",
    )
    assert [finding.location for finding in findings] == ["EEI-2"]
