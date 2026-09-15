"""An empty frozen selection publishes a limit without speculative model work."""

import pytest

from ase.application.reports.drafting import draft_body
from ase.application.reports.sections.quality import ensure_requirement_coverage
from ase.application.reports.templates import TEMPLATES
from ase.domain.evidence import quality_of_information
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.validation import Severity
from assistant_model_helpers import PROFILE
from section_model_helpers import HEADER, Checkpoints, Gateway, run


@pytest.mark.asyncio
async def test_resumable_empty_collection_abstains_without_checkpoint_or_model_call() -> None:
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints)
    requirements = tuple(
        IntelligenceRequirement(f"req-{number}", f"What changed in area {number}?")
        for number in range(1, 13)
    )

    draft = await run(gateway, checkpoints, evidence_items=(), canonical_requirements=requirements)

    assert draft.body is not None
    assert draft.body.key_judgements == ()
    assert draft.body.reporting == ()
    assert "No eligible evidence" in draft.body.sourcing_statement
    assert draft.attempts == 0
    assert draft.has_errors
    assert gateway.calls == checkpoints.writes == []
    body, findings = ensure_requirement_coverage(
        draft.body, None, supported=draft.supported_requirements, requirements=requirements
    )
    assert {gap.eei for gap in body.gaps if gap.eei} == {
        requirement.id for requirement in requirements
    }
    assert any(finding.severity is Severity.ERROR for finding in findings)


@pytest.mark.asyncio
async def test_one_off_empty_collection_uses_the_same_abstention() -> None:
    gateway = Gateway(Checkpoints())

    draft = await draft_body(
        gateway,
        PROFILE,
        "unused-key",
        TEMPLATES["ask"],
        HEADER,
        "What changed?",
        quality_of_information(()),
        (),
        (),
    )

    assert draft.body is not None
    assert draft.body.key_judgements == ()
    assert draft.body.sourcing_statement.startswith("No eligible evidence")
    assert [finding.rule for finding in draft.findings] == ["no_evidence"]
    assert draft.attempts == 0
    assert gateway.calls == []
