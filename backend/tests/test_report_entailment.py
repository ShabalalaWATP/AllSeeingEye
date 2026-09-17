"""The bounded entailment pass produces review reasons and never touches the report."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from ase.application.ports.llm import LlmGatewayError
from ase.application.reports.entailment import check_entailment, targets
from ase.domain.entailment import EntailmentParseError, parse_entailment
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmProfile, LlmRequest, LlmResult, LlmRole
from ase.domain.report_quality_rules import ENTAILMENT_RULE
from ase.domain.reports import (
    AssessmentSection,
    Confidence,
    KeyJudgement,
    Probability,
    ReportBody,
    ReportingItem,
    ReportingTheme,
)

NOW = datetime(2026, 9, 11, tzinfo=UTC)
PROFILE = LlmProfile(
    id=UUID(int=1),
    name="Local",
    base_url="http://localhost:11434/v1",
    model="llama3.1:8b",
    api_key_encrypted="encrypted",
    api_key_hint="test",
    roles=frozenset({LlmRole.ASSESSMENT}),
    max_output_tokens=4000,
    temperature=0.1,
    enabled=True,
    created_at=NOW,
    updated_at=NOW,
)


class FakeGateway:
    """Answers with scripted content; a string starting with '!' raises a gateway error."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.requests: list[LlmRequest] = []

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        self.requests.append(request)
        if self.answer.startswith("!"):
            raise LlmGatewayError(self.answer[1:])
        return LlmResult(
            content=self.answer,
            model=model,
            latency_ms=12.0,
            prompt_tokens=900,
            completion_tokens=80,
        )


def item(label: str) -> EvidenceItem:
    return EvidenceItem(
        label=label,
        event_id=f"ev-{label}",
        source_id="bbc_world",
        source_name="BBC World",
        independence_key="bbc",
        category="conflict",
        title=f"Reporting {label} on the crossing",
        summary="The crossing was quiet overnight.",
        url=None,
        published_at=NOW,
        captured_at=NOW,
        grade="B2",
        reliability="B",
        credibility=2,
        grade_rationale="",
        lon=None,
        lat=None,
        country_iso=None,
        content_hash=f"hash-{label}",
    )


EVIDENCE = (item("E1"), item("E2"))
BODY = ReportBody(
    key_judgements=(
        KeyJudgement(
            id="KJ1",
            statement="We assess it is likely that the crossing has closed.",
            probability=Probability.LIKELY,
            confidence=Confidence.MODERATE,
            confidence_statement="Information base: two items.",
            supporting_evidence=("E1", "E2"),
        ),
    ),
    reporting=(ReportingTheme("Crossing", (ReportingItem("Quiet.", ("E1",), "B2"),)),),
    assessment=(AssessmentSection("Trajectory", "Steady.", ("E1",)),),
    sourcing_statement="One organisation.",
)


def answer(*rows: tuple[str, str, str, str]) -> str:
    return json.dumps(
        {
            "assessments": [
                {"judgement_id": row[0], "label": row[1], "verdict": row[2], "reason": row[3]}
                for row in rows
            ]
        }
    )


async def run(content: str) -> object:
    gateway = FakeGateway(content)
    return await check_entailment(gateway, PROFILE, "key", BODY, EVIDENCE)


async def test_supporting_verdicts_produce_no_review_reason() -> None:
    draft = await run(
        answer(("KJ1", "E1", "supports", "It says so."), ("KJ1", "E2", "supports", ""))
    )
    assert draft.ran and draft.reasons == [] and draft.findings == []
    assert draft.prompt_tokens == 900


async def test_an_unsupported_citation_becomes_an_error_reason_naming_it() -> None:
    draft = await run(answer(("KJ1", "E1", "does_not_support", "It covers a different crossing.")))
    assert [finding.severity.value for finding in draft.reasons] == ["error"]
    message = draft.reasons[0].message
    assert draft.reasons[0].rule == ENTAILMENT_RULE and draft.reasons[0].location == "KJ1"
    assert "E1" in message and "the crossing has closed" in message
    assert "It covers a different crossing." in message
    assert "not a check of whether the judgement is true" in message


async def test_a_partial_verdict_is_advisory() -> None:
    draft = await run(answer(("KJ1", "E2", "partly_supports", "Different date.")))
    assert [finding.severity.value for finding in draft.reasons] == ["warning"]


async def test_an_unavailable_model_degrades_honestly() -> None:
    draft = await run("!no route to the endpoint")
    assert not draft.ran and draft.reasons == []
    assert [finding.severity.value for finding in draft.findings] == ["warning"]
    assert "did not run" in draft.findings[0].message


async def test_an_unusable_answer_is_reported_without_failing_the_report() -> None:
    draft = await run("not json at all")
    assert not draft.ran and draft.reasons == []
    assert "unusable answer" in draft.findings[0].message


async def test_a_verdict_on_a_pair_that_was_never_asked_about_is_dropped() -> None:
    draft = await run(
        answer(("KJ9", "E1", "does_not_support", "Invented."), ("KJ1", "E1", "supports", ""))
    )
    assert draft.ran and draft.reasons == []
    assert [row.judgement_id for row in draft.rows] == ["KJ1"]


async def test_the_prompt_is_bounded_to_the_key_judgements_and_their_citations() -> None:
    wide = replace(
        BODY,
        key_judgements=tuple(
            replace(BODY.key_judgements[0], id=f"KJ{index}") for index in range(1, 9)
        ),
    )
    assert len({row[0] for row in targets(wide, EVIDENCE)}) == 5
    gateway = FakeGateway(answer(("KJ1", "E1", "supports", "")))
    await check_entailment(gateway, PROFILE, "key", BODY, EVIDENCE)
    request = gateway.requests[0]
    assert request.schema_name == "entailment"
    assert request.max_output_tokens <= PROFILE.max_output_tokens
    assert "Assess the pair (KJ1, E1)." in request.messages[1].content


def test_an_unknown_verdict_is_rejected() -> None:
    with pytest.raises(EntailmentParseError):
        parse_entailment(
            {"assessments": [{"judgement_id": "KJ1", "label": "E1", "verdict": "yes"}]},
            frozenset({("KJ1", "E1")}),
        )
    with pytest.raises(EntailmentParseError):
        parse_entailment({"assessments": "no"}, frozenset())
