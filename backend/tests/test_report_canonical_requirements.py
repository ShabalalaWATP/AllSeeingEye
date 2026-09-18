"""Twelve authored requirements survive planning, section resume and coverage."""

import json
from dataclasses import replace

from ase.application.reports.document import build_document
from ase.application.reports.production_version import header_for
from ase.application.reports.prompts import compose_messages
from ase.application.reports.publication_markdown import render_document_markdown
from ase.application.reports.sections.planning import packet_digest, plan_topics
from ase.application.reports.sections.prompts import PromptContext
from ase.application.reports.sections.quality import ensure_requirement_coverage
from ase.application.reports.selection import Selection
from ase.application.reports.templates import TEMPLATES
from ase.container import Container
from ase.domain.direction import Direction
from ase.domain.evidence import quality_of_information
from ase.domain.report_input import parse_model_body
from ase.domain.research import ResearchMode
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.users import User
from assistant_model_helpers import PROFILE
from production_integration_helpers import production_job
from report_documents_helpers import document_records
from section_model_helpers import HEADER, Checkpoints, Gateway, items, run
from test_report_integrity import sound_body

NAMES = (
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
)


def requirements() -> tuple[IntelligenceRequirement, ...]:
    return tuple(
        IntelligenceRequirement(
            "r" * 64 if index == 12 else f"req-{index:02d}",
            (f"What does {name} show? " + "Detailed evidence question. " * 13).rstrip(),
            required=index != 12,
            priority=index,
        )
        for index, name in enumerate(NAMES, 1)
    )


def selected():
    return tuple(
        replace(item, title=f"{name} observation")
        for item, name in zip(items(12), NAMES, strict=True)
    )


def digest(requirements_to_use):
    evidence = selected()
    return packet_digest(
        PROFILE,
        TEMPLATES["ask"],
        HEADER,
        "What changed?",
        quality_of_information(evidence),
        evidence,
        (),
        None,
        None,
        requirements=requirements_to_use,
    )


def test_planning_and_prompt_keep_all_twelve_exact_ids_and_questions() -> None:
    authored = requirements()
    evidence = selected()
    legacy = Direction("Different model question", eeis=("Model EEI",))
    topics = plan_topics(evidence, legacy, requirements=authored)
    bindings = [row for topic in topics for row in topic.requirement_evidence]
    assert len(topics) <= 6
    assert {identifier for identifier, _ in bindings} == {row.id for row in authored}
    assert {label for _, labels in bindings for label in labels} == {
        item.label for item in evidence
    }
    context = PromptContext(
        TEMPLATES["ask"],
        HEADER,
        "What changed?",
        quality_of_information(evidence),
        evidence,
        (),
        legacy,
        None,
        authored,
    )
    system, user = context.messages(topics[0])
    payload = json.loads(user.content)
    assert payload["canonical_requirements"] == [
        {"id": row.id, "question": row.question, "required": row.required, "priority": row.priority}
        for row in authored
    ]
    assert payload["direction"] == []
    assert "requirement_evidence pairs each requirement" in system.content
    assert len(authored[-1].question) > 300
    assert digest(authored) != digest(
        (*authored[:-1], replace(authored[-1], question="New exact question"))
    )


async def test_checkpoint_resume_and_coverage_keep_all_twelve_ids() -> None:
    authored = requirements()
    evidence = selected()
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints)
    first = await run(gateway, checkpoints, evidence, canonical_requirements=authored)
    assert first.body is not None
    assert first.supported_requirements is not None
    unresolved = {row.id for row in authored} - first.supported_requirements
    assert {row.eei for row in first.body.gaps} == unresolved
    assert len(unresolved) > 0
    before = len(gateway.calls)
    resumed = await run(gateway, checkpoints, evidence, canonical_requirements=authored)
    assert resumed.body == first.body and len(gateway.calls) == before
    changed = (*authored[:-1], replace(authored[-1], question="New exact question"))
    await run(gateway, checkpoints, evidence, canonical_requirements=changed)
    assert len(gateway.calls) > before


def test_required_coverage_errors_and_optional_gaps_remain_distinct() -> None:
    authored = requirements()
    body = parse_model_body(sound_body())
    covered, findings = ensure_requirement_coverage(
        body,
        Direction("Ignored legacy", eeis=("Different EEI",)),
        supported=frozenset(),
        requirements=authored,
    )
    assert [row.eei for row in covered.gaps[:12]] == [row.id for row in authored]
    assert {finding.location for finding in findings} == {
        row.id for row in authored if row.required
    }
    assert all("Detailed evidence question" in row.text for row in covered.gaps[:12])
    assert all(row.eei != "EEI-1" for row in covered.gaps)


def test_single_call_prompt_uses_authored_requirements_instead_of_model_eeis() -> None:
    authored = requirements()
    messages = compose_messages(
        TEMPLATES["ask"],
        scope_line="Twelve requirements",
        period_from=HEADER.period_from,
        period_to=HEADER.period_to,
        question="What changed?",
        quality=quality_of_information(selected()),
        evidence=selected(),
        direction=Direction("Legacy", eeis=("Model EEI",)),
        canonical_requirements=authored,
    )
    text = messages[1].content
    assert all(f"{row.id} (" in text and row.question in text for row in authored)
    assert "Model EEI" not in text


def test_frozen_version_document_and_markdown_export_exact_requirement_text() -> None:
    authored = requirements()
    record, version = document_records()
    document = build_document(record, replace(version, canonical_requirements=authored))
    markdown = render_document_markdown(document)
    assert "The research questions" in markdown
    frozen_text = "\n".join(block.text for block in document.blocks)
    for row in authored:
        assert row.question in frozen_text
        assert row.id in markdown
        assert row.question in markdown


def test_production_header_uses_canonical_ids_instead_of_model_eeis(
    container: Container, user: User
) -> None:
    authored = requirements()
    job = production_job(user, container.cipher)
    job = replace(
        job,
        request=replace(
            job.request,
            research_mode=ResearchMode.ADVANCED,
            canonical_requirements=authored,
        ),
    )
    header = header_for(job, Selection(items(1), 0, 1), Direction("Legacy", eeis=("Model EEI",)))
    assert header.requirements == tuple(row.id for row in authored)
