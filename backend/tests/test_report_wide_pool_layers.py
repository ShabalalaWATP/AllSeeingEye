"""A wide pool is read in more, smaller passes, inside the unchanged leaf ceiling."""

from dataclasses import replace

import pytest

from ase.application.ports.llm import LlmGatewayError
from ase.application.reports.drafting import FLAT_DRAFT_NOTICE, draft_body
from ase.application.reports.sections.planning import (
    MAX_INITIAL_TOPICS,
    MAX_TOPIC_EVIDENCE,
    MAX_TOPIC_LEAVES,
    MAX_WIDE_TOPICS,
    WIDE_POOL_ITEMS,
    WIDE_SUFFIX,
    method_for,
    packet_digest,
    plan_topics,
)
from ase.application.reports.templates import TEMPLATES
from ase.domain.direction import Direction
from ase.domain.evidence import quality_of_information
from ase.domain.validation import Severity
from assistant_model_helpers import PROFILE
from section_model_helpers import HEADER, items

DIRECTION = Direction(pir="What changed?", eeis=("Substations struck?", "Repairs made?"))


def evidence(count: int):
    return tuple(
        replace(row, title=f"Distinct reporting item {index} on theme {index % 5}")
        for index, row in enumerate(items(count), 1)
    )


def test_a_narrow_pool_keeps_its_existing_topic_ceiling_and_digest():
    pool = evidence(30)
    topics = plan_topics(pool, DIRECTION)
    assert len(topics) <= MAX_INITIAL_TOPICS
    assert method_for("report-sections-v3", len(pool)) == "report-sections-v3"


def test_a_wide_pool_is_split_into_more_bounded_passes():
    narrow = plan_topics(evidence(WIDE_POOL_ITEMS), DIRECTION)
    wide = plan_topics(evidence(96), DIRECTION)
    assert len(narrow) <= MAX_INITIAL_TOPICS
    assert MAX_INITIAL_TOPICS < len(wide) <= MAX_WIDE_TOPICS
    assert max(len(topic.evidence_labels) for topic in wide) <= MAX_TOPIC_EVIDENCE
    # Every item still reaches exactly one pass; nothing is dropped by layering.
    assigned = [label for topic in wide for label in topic.evidence_labels]
    assert sorted(assigned, key=lambda label: int(label[1:])) == [f"E{n}" for n in range(1, 97)]


def test_layering_never_raises_the_call_ceiling():
    wide = plan_topics(evidence(96), DIRECTION)
    assert len(wide) <= MAX_TOPIC_LEAVES
    # Splits on exhaustion still have room inside the same unchanged leaf ceiling.
    assert MAX_TOPIC_LEAVES - len(wide) >= 3


def test_a_wide_plan_declares_its_layering_in_the_packet_digest():
    pool = evidence(96)
    values = (
        PROFILE,
        TEMPLATES["intsum"],
        HEADER,
        "What changed?",
        quality_of_information(pool),
        pool,
        (),
        DIRECTION,
        None,
    )
    assert method_for("report-sections-v3", len(pool)).endswith(WIDE_SUFFIX)
    narrow_values = (*values[:5], evidence(10), *values[6:])
    assert packet_digest(*values) != packet_digest(*narrow_values)


@pytest.mark.anyio
async def test_the_flat_path_says_plainly_that_it_read_a_wide_pool_in_one_go():
    pool = evidence(WIDE_POOL_ITEMS + 1)

    class FailingGateway:
        async def complete(self, base_url, api_key, model, request):
            raise LlmGatewayError("unavailable")

    draft = await draft_body(
        FailingGateway(),
        PROFILE,
        "key",
        TEMPLATES["intsum"],
        HEADER,
        "What changed?",
        quality_of_information(pool),
        pool,
        (),
    )
    notice = [row for row in draft.findings if row.rule == "evidence_volume"]
    assert len(notice) == 1
    assert notice[0].severity is Severity.WARNING
    assert notice[0].message == FLAT_DRAFT_NOTICE


@pytest.mark.anyio
async def test_a_narrow_flat_draft_carries_no_volume_notice():
    pool = evidence(5)

    class FailingGateway:
        async def complete(self, base_url, api_key, model, request):
            raise LlmGatewayError("unavailable")

    draft = await draft_body(
        FailingGateway(),
        PROFILE,
        "key",
        TEMPLATES["intsum"],
        HEADER,
        "What changed?",
        quality_of_information(pool),
        pool,
        (),
    )
    assert not [row for row in draft.findings if row.rule == "evidence_volume"]
