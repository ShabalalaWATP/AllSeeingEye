"""A requirement is not answered merely because an item was selected."""

import json
from dataclasses import replace

from ase.application.reports.sections.planning import Topic
from ase.application.reports.sections.quality import (
    CoverageState,
    project_requirement_coverage,
    requirement_support_from_topics,
)
from ase.domain.research import ResearchMode
from ase.domain.research_brief_values import IntelligenceRequirement
from section_model_helpers import HEADER, Checkpoints, Gateway, run
from test_report_canonical_requirements import requirements, selected


def test_exact_bound_citations_gaps_and_contrary_evidence_define_four_states():
    rows = tuple(
        IntelligenceRequirement(f"req-{index}", f"Question {index}?", required=True)
        for index in range(1, 5)
    )
    topic = Topic(
        "S1",
        "Mixed packet",
        ("E1", "E2", "E3", "E4", "E5"),
        requirement_evidence=(
            ("req-1", ("E1",)),
            ("req-2", ("E2",)),
            ("req-3", ("E3", "E4")),
            ("req-4", ("E5",)),
        ),
    )
    body = {
        "reporting": [
            {"evidence": ["E1", "E2", "E3"]},
        ],
        "assessment": [{"evidence": ["E1", "E3", "E4"]}],
        "gaps": [{"eei": "req-2", "text": "No independent confirmation."}],
    }
    projected = project_requirement_coverage(
        [(topic, body)],
        requirements=rows,
        judgements={
            "key_judgements": [{"supporting_evidence": ["E3"], "contradicting_evidence": ["E4"]}]
        },
    )

    assert [row.requirement_id for row in projected] == [row.id for row in rows]
    assert [row.state for row in projected] == [
        CoverageState.ANSWERED,
        CoverageState.PARTIALLY_ANSWERED,
        CoverageState.DISPUTED,
        CoverageState.NO_ADEQUATE_EVIDENCE,
    ]
    assert projected[1].selected_evidence == projected[1].cited_evidence == ("E2",)
    assert projected[1].gap_count == 1
    assert projected[3].selected_evidence == ("E5",)
    assert projected[3].cited_evidence == ()
    assert requirement_support_from_topics(
        [(topic, body)],
        requirements=rows,
        judgements={
            "key_judgements": [{"supporting_evidence": ["E3"], "contradicting_evidence": ["E4"]}]
        },
    ) == {"req-1"}


async def test_all_twelve_authored_requirements_reach_both_synthesis_calls():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints)
    authored = requirements()
    header = replace(HEADER, scope={"research_mode": ResearchMode.ADVANCED.value})
    await run(
        gateway,
        checkpoints,
        selected(),
        header=header,
        canonical_requirements=authored,
    )
    for _, request, *_ in gateway.calls[-2:]:
        payload = json.loads(request.messages[1].content)
        manifest = payload["requirement_coverage_manifest"]
        assert len(manifest) == 12
        assert [row["requirement_id"] for row in manifest] == [row.id for row in authored]
        assert all("state" in row and "cited_evidence" in row for row in manifest)
        assert "not verification" in request.messages[0].content


def test_legacy_unbound_topics_do_not_claim_a_coverage_result():
    topic = Topic("S1", "Historic topic", ("E1",))
    body = {"reporting": [], "assessment": [], "gaps": []}
    assert project_requirement_coverage([(topic, body)]) == ()
