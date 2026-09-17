"""The disagreement pass explains a conflict without deciding it, and degrades honestly."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from ase.application.ports.llm import LlmGatewayError
from ase.application.reports.contradiction_pass import contested, explain_contradictions
from ase.application.reports.production_model_roles import explain_for_job
from ase.application.reports.production_types import Job, Totals
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import TEMPLATES
from ase.domain.contradiction_analysis import ContradictionParseError, parse_disagreements
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmProfile, LlmRequest, LlmResult, LlmRole
from ase.domain.report_quality_rules import CONTRADICTION_RULE
from ase.domain.reports import (
    AssessmentSection,
    Confidence,
    KeyJudgement,
    Probability,
    ReportBody,
    ReportingItem,
    ReportingTheme,
)
from ase.domain.users import Role, User

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


ACTOR = User(
    UUID(int=7),
    "quality@example.invalid",
    "Quality",
    Role.USER,
    True,
    "hash",
    0,
    None,
    None,
    NOW,
    None,
)
JOB = Job(
    ACTOR,
    TEMPLATES["intsum"],
    ReportRequest("intsum"),
    PROFILE,
    NOW,
    timedelta(hours=48),
    "Intelligence summary",
    {},
    None,
)


class Cipher:
    available = True

    def encrypt(self, plaintext: str) -> str:
        return plaintext

    def decrypt(self, ciphertext: str) -> str:
        return ciphertext


CIPHER = Cipher()


class FakeGateway:
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
            latency_ms=9.0,
            prompt_tokens=700,
            completion_tokens=60,
        )


def item(label: str, source_id: str, name: str) -> EvidenceItem:
    return EvidenceItem(
        label=label,
        event_id=f"ev-{label}",
        source_id=source_id,
        source_name=name,
        independence_key=source_id,
        category="conflict",
        title=f"{name} on the crossing",
        summary="The crossing is described differently.",
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


EVIDENCE = (item("E1", "bbc_world", "BBC World"), item("E2", "tass_en", "TASS"))
BODY = ReportBody(
    key_judgements=(
        KeyJudgement(
            id="KJ1",
            statement="We assess it is likely that the crossing has closed.",
            probability=Probability.LIKELY,
            confidence=Confidence.MODERATE,
            confidence_statement="Information base: two items.",
            supporting_evidence=("E1",),
            contradicting_evidence=("E2",),
        ),
    ),
    reporting=(ReportingTheme("Crossing", (ReportingItem("Quiet.", ("E1",), "B2"),)),),
    assessment=(AssessmentSection("Trajectory", "Steady.", ("E1",)),),
    sourcing_statement="Two organisations.",
)


def answer(*rows: tuple[str, str, str]) -> str:
    return json.dumps(
        {
            "disagreements": [
                {"judgement_id": row[0], "point": row[1], "explanation": row[2]} for row in rows
            ]
        }
    )


async def test_the_point_at_issue_is_reported_as_an_advisory_note() -> None:
    gateway = FakeGateway(
        answer(("KJ1", "the date the crossing shut", "One says Tuesday, the other Friday."))
    )
    draft = await explain_contradictions(gateway, PROFILE, "key", BODY, EVIDENCE)
    assert draft.ran and len(draft.reasons) == 1
    note = draft.reasons[0]
    assert (note.rule, note.location, note.severity.value) == (
        CONTRADICTION_RULE,
        "KJ1",
        "warning",
    )
    assert "disagree about the date the crossing shut" in note.message
    assert "did not decide which source is right" in note.message
    request = gateway.requests[0]
    assert request.schema_name == "contradiction_analysis"
    assert "E1 (BBC World, graded B2)" in request.messages[1].content
    assert "E2 (TASS, graded B2)" in request.messages[1].content


async def test_a_judgement_with_no_cited_counterevidence_costs_nothing() -> None:
    uncontested = replace(
        BODY, key_judgements=(replace(BODY.key_judgements[0], contradicting_evidence=()),)
    )
    gateway = FakeGateway(answer(("KJ1", "nothing", "")))
    draft = await explain_contradictions(gateway, PROFILE, "key", uncontested, EVIDENCE)
    assert contested(uncontested) == () and gateway.requests == []
    assert not draft.ran and draft.reasons == [] and draft.findings == []


async def test_an_unavailable_model_leaves_the_mechanical_naming_to_stand() -> None:
    draft = await explain_contradictions(
        FakeGateway("!endpoint refused"), PROFILE, "key", BODY, EVIDENCE
    )
    assert not draft.ran and draft.reasons == []
    assert "still named" in draft.findings[0].message
    assert draft.findings[0].severity.value == "warning"


async def test_an_unusable_answer_is_reported_and_nothing_else_changes() -> None:
    draft = await explain_contradictions(FakeGateway("<html>"), PROFILE, "key", BODY, EVIDENCE)
    assert not draft.ran and "unusable answer" in draft.findings[0].message


def test_rows_about_other_judgements_or_with_no_point_are_dropped() -> None:
    parsed = parse_disagreements(
        {
            "disagreements": [
                {"judgement_id": "KJ9", "point": "invented", "explanation": ""},
                {"judgement_id": "KJ1", "point": "", "explanation": "no point given"},
                {"judgement_id": "KJ1", "point": "the count", "explanation": "40 against 400"},
            ]
        },
        frozenset({"KJ1"}),
    )
    assert [row.point for row in parsed] == ["the count"]
    with pytest.raises(ContradictionParseError):
        parse_disagreements({"disagreements": {}}, frozenset({"KJ1"}))


async def test_the_job_step_skips_the_call_when_nothing_is_contested() -> None:
    gateway = FakeGateway(answer(("KJ1", "nothing", "")))
    uncontested = replace(
        BODY, key_judgements=(replace(BODY.key_judgements[0], contradicting_evidence=()),)
    )
    totals = Totals()

    async def profile_for(role: LlmRole) -> LlmProfile | None:
        return PROFILE

    await explain_for_job(JOB, profile_for, uncontested, EVIDENCE, totals, gateway, CIPHER)
    assert gateway.requests == [] and totals.usage == [] and totals.findings == []


async def test_the_job_step_says_so_when_no_profile_plays_the_role() -> None:
    totals = Totals()

    async def profile_for(role: LlmRole) -> LlmProfile | None:
        return None

    await explain_for_job(JOB, profile_for, BODY, EVIDENCE, totals, FakeGateway("{}"), CIPHER)
    assert totals.usage == []
    assert [finding.rule for finding in totals.findings] == [CONTRADICTION_RULE]
    assert "still named" in totals.findings[0].message
