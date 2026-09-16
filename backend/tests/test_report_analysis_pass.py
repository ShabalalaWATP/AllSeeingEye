"""The template budgets, the analysis demands and the dedicated analysis pass."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from ase.application.reports.analysis import STAGE_ID, analysis_digest, run_analysis
from ase.application.reports.prompts import ANALYSIS_STANDARD, compose_messages, template_guidance
from ase.application.reports.sections.prompts import PromptContext
from ase.application.reports.templates import TEMPLATES, template_for
from ase.domain.evidence import quality_of_information
from ase.domain.llm import MAX_OUTPUT_TOKENS
from ase.domain.report_diagrams import DiagramKind
from report_analysis_helpers import (
    TIMELINE,
    AnalysisGateway,
    MemoryCheckpoints,
    analysis_inputs,
    analysis_payload,
    analysis_profile,
    exhausted,
    gateway_error,
)

pytestmark = pytest.mark.anyio


def test_every_product_has_room_for_prose_and_a_bounded_analysis_pass() -> None:
    for template in TEMPLATES.values():
        assert 10_000 <= template.token_budget <= MAX_OUTPUT_TOKENS
        assert 0 < template.analysis_budget <= template.token_budget
        assert template.sections and template.analysis_focus


def test_section_guidance_demands_analysis_and_keeps_the_doctrine_rules() -> None:
    for template in TEMPLATES.values():
        joined = " ".join(template.sections).lower()
        assert "alternative" in joined or "competing" in joined
        assert "falsif" in joined or "wrong" in joined or "overturn" in joined
        assert ("yardstick" in joined and "grade" in joined) or "cited" in joined
    intsum = " ".join(TEMPLATES["intsum"].sections).lower()
    assert "no yardstick terms" in intsum
    assert "as assessment, distinct from what was reported" in intsum


def test_template_guidance_carries_the_product_questions() -> None:
    guidance = template_guidance(TEMPLATES["conflict_assessment"])
    for question in TEMPLATES["conflict_assessment"].analysis_focus:
        assert question in guidance


def test_both_drafting_paths_receive_the_analysis_standard() -> None:
    header, _body, evidence = analysis_inputs()
    single = compose_messages(
        template_for("intsum"),
        scope_line="Test",
        period_from=header.period_from,
        period_to=header.period_to,
        question=None,
        quality=quality_of_information(evidence),
        evidence=evidence,
    )
    assert ANALYSIS_STANDARD in single[0].content
    context = PromptContext(
        template_for("intsum"),
        header,
        None,
        quality_of_information(evidence),
        evidence,
        (),
        None,
        None,
    )
    topic_system = context.messages(None, synthesis_step="synthesis_judgements")[0].content
    assert ANALYSIS_STANDARD in topic_system
    assert "Sections and guidance:" in topic_system


async def test_analysis_pass_appends_assessment_without_touching_reporting() -> None:
    header, body, evidence = analysis_inputs()
    gateway = AnalysisGateway()
    outcome = await run_analysis(
        gateway, analysis_profile(), "key", template_for("intsum"), header, body, evidence
    )
    assert outcome.performed and len(outcome.sections) == 2
    extended = outcome.apply(body)
    assert extended.reporting == body.reporting
    assert extended.key_judgements == body.key_judgements
    assert len(extended.assessment) == len(body.assessment) + 2
    assert "competing explanation" in extended.assessment[-1].heading.lower()


async def test_analysis_pass_is_metered_within_the_product_budget() -> None:
    header, body, evidence = analysis_inputs()
    gateway = AnalysisGateway()
    template = template_for("conflict_assessment")
    await run_analysis(gateway, analysis_profile(), "key", template, header, body, evidence)
    request = gateway.requests[0]
    assert request.max_output_tokens == template.analysis_budget
    assert request.schema_name == "report_analysis"
    small = analysis_profile(max_output_tokens=1_500)
    await run_analysis(gateway, small, "key", template, header, body, evidence)
    assert gateway.requests[1].max_output_tokens == 1_500


async def test_a_product_without_an_analysis_budget_makes_no_call() -> None:
    header, body, evidence = analysis_inputs()
    gateway = AnalysisGateway()
    template = replace(template_for("intsum"), analysis_budget=0)
    outcome = await run_analysis(
        gateway, analysis_profile(), "key", template, header, body, evidence
    )
    assert not gateway.requests and not outcome.performed and not outcome.attempts
    assert "does not run an analysis pass" in outcome.skipped_reason
    assert outcome.apply(body) == body


async def test_a_body_without_reporting_makes_no_call() -> None:
    header, body, evidence = analysis_inputs()
    gateway = AnalysisGateway()
    outcome = await run_analysis(
        gateway,
        analysis_profile(),
        "key",
        template_for("intsum"),
        header,
        replace(body, reporting=()),
        evidence,
    )
    assert not gateway.requests and outcome.skipped_reason == "no drafted reporting to analyse"


@pytest.mark.parametrize("failure", [gateway_error, exhausted])
async def test_a_failed_analysis_pass_degrades_honestly(failure: object) -> None:
    header, body, evidence = analysis_inputs()
    gateway = AnalysisGateway(failure=failure())  # type: ignore[operator]
    outcome = await run_analysis(
        gateway, analysis_profile(), "key", template_for("intsum"), header, body, evidence
    )
    assert not outcome.performed and outcome.attempts == 1
    assert outcome.apply(body) == body
    assert [row.rule for row in outcome.findings] == ["analysis"]
    assert outcome.skipped_reason


async def test_an_off_contract_answer_leaves_the_drafted_body_alone() -> None:
    header, body, evidence = analysis_inputs()
    gateway = AnalysisGateway(json.dumps({"sections": [], "diagram": None}))
    outcome = await run_analysis(
        gateway, analysis_profile(), "key", template_for("intsum"), header, body, evidence
    )
    assert not outcome.performed and outcome.apply(body) == body


async def test_sections_citing_evidence_outside_the_report_are_dropped() -> None:
    header, body, evidence = analysis_inputs()
    payload = json.dumps(
        {
            "sections": [
                {"heading": "Unsupported", "text": "A claim.", "evidence": ["E900"]},
                {"heading": "Supported", "text": "A cited claim.", "evidence": ["E1", "E900"]},
            ],
            "diagram": None,
        }
    )
    outcome = await run_analysis(
        AnalysisGateway(payload),
        analysis_profile(),
        "key",
        template_for("intsum"),
        header,
        body,
        evidence,
    )
    assert [row.heading for row in outcome.sections] == ["Supported"]
    assert outcome.sections[0].evidence == ("E1",)


async def test_a_completed_pass_resumes_from_its_checkpoint_without_paying_again() -> None:
    header, body, evidence = analysis_inputs()
    checkpoints = MemoryCheckpoints()
    profile, template = analysis_profile(), template_for("intsum")
    gateway = AnalysisGateway(analysis_payload(TIMELINE))
    first = await run_analysis(
        gateway, profile, "key", template, header, body, evidence, checkpoints=checkpoints
    )
    assert first.performed and first.diagram is not None
    digest = analysis_digest(profile, template, header, body, evidence)
    assert (digest, STAGE_ID) in checkpoints.saved
    second = await run_analysis(
        gateway, profile, "key", template, header, body, evidence, checkpoints=checkpoints
    )
    assert len(gateway.requests) == 1
    assert second.performed and second.sections == first.sections
    assert second.diagram is not None and second.diagram.kind is DiagramKind.TIMELINE
