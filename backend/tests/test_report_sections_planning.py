"""Plans preserve every original label and have deterministic bounded split lineage."""

from dataclasses import replace

import pytest

from ase.application.reports.sections.planning import (
    LEGACY_METHOD_VERSION,
    packet_digest,
    plan_topics,
    split_topic,
    topic_ceiling,
)
from ase.application.reports.sections.quality import requirement_support_from_topics
from ase.application.reports.templates import TEMPLATES
from ase.domain.direction import Direction
from ase.domain.evidence import quality_of_information
from ase.domain.llm import ReasoningEffort
from assistant_model_helpers import PROFILE
from section_model_helpers import HEADER, items


@pytest.mark.parametrize("count", [1, 2, 3, 4, 6, 20, 50, 100])
def test_plan_covers_every_label_once_without_inventing_small_packet_topics(count):
    evidence = items(count)
    topics = plan_topics(evidence, None)
    assert topics == plan_topics(evidence, None)
    labels = [label for topic in topics for label in topic.evidence_labels]
    assert len(labels) == len(set(labels)) == count and set(labels) == {
        row.label for row in evidence
    }
    ceiling = topic_ceiling(count)
    assert len(topics) == 1 if count <= 2 else min(4, count) <= len(topics) <= ceiling
    assert all(topic.evidence_labels and len(topic.title) <= 120 for topic in topics)


def test_topics_use_matching_eeis_and_declared_category_country_without_guessing():
    evidence = tuple(
        replace(
            row,
            category="maritime",
            country_iso="GB" if index % 2 else None,
            title="Nuclear inspection" if index < 3 else "Port movement",
        )
        for index, row in enumerate(items(12))
    )
    topics = plan_topics(
        evidence, Direction("What changed?", eeis=("Nuclear inspections", "Unknown topic"))
    )
    assert any(topic.eei_ids == ("EEI-1",) for topic in topics)
    assert not any("Unknown topic" in topic.title for topic in topics)
    assert any("Maritime (GB)" in topic.title for topic in topics)


def test_common_country_context_cannot_assign_every_item_to_the_first_eei():
    evidence = tuple(
        replace(
            row,
            country_iso="RU",
            title="Russia nuclear inspection" if index == 0 else f"Russia general update {index}",
        )
        for index, row in enumerate(items(12))
    )
    direction = Direction(
        "What changed?",
        eeis=(
            "Which nuclear inspections occurred in Russia?",
            "Which military satellite movements occurred in Russia?",
        ),
    )
    topics = plan_topics(evidence, direction)
    first = next(topic for topic in topics if topic.eei_ids == ("EEI-1",))
    assert first.evidence_labels == ("E1",)
    assert not any(topic.eei_ids == ("EEI-2",) for topic in topics)

    legacy = plan_topics(evidence, direction, method_version=LEGACY_METHOD_VERSION)
    assert {
        label for topic in legacy if topic.eei_ids == ("EEI-1",) for label in topic.evidence_labels
    } == {row.label for row in evidence}


def test_small_packet_keeps_unambiguous_requirement_evidence_binding():
    evidence = (replace(items(1)[0], title="Nuclear inspection completed"),)
    direction = Direction("What changed?", eeis=("Which nuclear inspection was completed?",))

    topic = plan_topics(evidence, direction)[0]
    support = requirement_support_from_topics(
        [
            (
                topic,
                {
                    "reporting": [{"evidence": ["E1"]}],
                    "assessment": [{"evidence": ["E1"]}],
                    "gaps": [],
                },
            )
        ]
    )

    assert topic.title == "Supplied evidence"
    assert topic.requirement_evidence == (("EEI-1", ("E1",)),)
    assert support == {"EEI-1"}


def test_folded_topic_supports_only_requirements_whose_bound_evidence_is_cited():
    subjects = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")
    evidence = tuple(
        replace(row, title=f"{subject} observation", category=f"category-{index}")
        for index, (row, subject) in enumerate(zip(items(8), subjects, strict=True))
    )
    direction = Direction(
        "What changed?",
        eeis=tuple(f"What does {subject} establish?" for subject in subjects),
    )

    folded = plan_topics(evidence, direction)[-1]
    cited_requirement, cited_labels = folded.requirement_evidence[0]
    support = requirement_support_from_topics(
        [
            (
                folded,
                {
                    "reporting": [{"evidence": [cited_labels[0]]}],
                    "assessment": [{"evidence": [cited_labels[0]]}],
                    "gaps": [],
                },
            )
        ]
    )

    assert len(folded.requirement_evidence) == 3
    assert support == {cited_requirement}


def test_many_categories_merge_tail_without_dropping_or_duplicate_labels():
    evidence = tuple(
        replace(row, category=f"category-{index}") for index, row in enumerate(items(10))
    )
    topics = plan_topics(evidence, None)
    assert len(topics) == 6 and topics[-1].title == "Further supplied evidence"
    assert set(topics[-1].evidence_labels) == {f"E{x}" for x in range(6, 11)}


def test_split_children_are_smaller_disjoint_and_stop_after_two_levels():
    parent = plan_topics(items(100), None)[0]
    children = split_topic(parent)
    assert children and all(child.parent == parent.id and child.depth == 1 for child in children)
    assert set(children[0].evidence_labels).isdisjoint(children[1].evidence_labels)
    assert set(parent.evidence_labels) == {
        label for child in children for label in child.evidence_labels
    }
    grandchildren = split_topic(children[0])
    assert grandchildren and split_topic(grandchildren[0]) is None
    assert split_topic(plan_topics(items(1), None)[0]) is None


@pytest.mark.parametrize(
    "evidence",
    [(), items(101), (items(1)[0], items(1)[0]), (replace(items(1)[0], label="description E1"),)],
)
def test_invalid_frozen_packets_are_rejected(evidence):
    with pytest.raises(ValueError):
        plan_topics(evidence, None)


def digest(evidence=None, profile=PROFILE, header=HEADER, background=None):
    selected = items() if evidence is None else evidence
    return packet_digest(
        profile,
        TEMPLATES["ask"],
        header,
        "Question",
        quality_of_information(selected),
        selected,
        (),
        None,
        background,
    )


def test_digest_binds_full_evidence_provenance_scope_profile_and_background():
    baseline = digest()
    assert baseline == digest() and len(baseline) == 64
    changed = list(items())
    changed[0] = replace(changed[0], grade="A1", reliability="A", country_iso="UA")
    variants = [
        digest(tuple(changed)),
        digest(profile=replace(PROFILE, reasoning_effort=ReasoningEffort.HIGH)),
        digest(profile=replace(PROFILE, api_key_encrypted="replacement-test-cipher")),
        digest(header=replace(HEADER, scope={"report_language": "fr"})),
        digest(background="New context"),
    ]
    assert len({baseline, *variants}) == 6
    assert "test" not in baseline
