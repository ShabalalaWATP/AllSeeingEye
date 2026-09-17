"""Mechanical model work runs at a capped reasoning effort; analysis keeps the operator's."""

from __future__ import annotations

import pytest

from ase.adapters.llm.effort import MechanicalEffortGateway
from ase.domain.llm import LlmMessage, LlmRequest, LlmResult, ReasoningEffort
from ase.domain.reasoning import (
    DEFAULT_MECHANICAL_EFFORT,
    MECHANICAL_PURPOSES,
    ReasoningEffortPolicy,
    parse_mechanical_effort,
    parse_mechanical_purposes,
)
from ase.infrastructure.settings import Settings

ANALYTICAL = (
    "report",
    "report_topic",
    "report_judgements",
    "report_context",
    "report_alternatives",
    "report_collection",
    "direction",
    "advocacy",
    "challenge_plan",
    "challenge_reviews",
    "eye_assistant",
    "research_plan",
    "research_replan",
    "research_continuation",
    "photo_geolocation",
)


class RecordingGateway:
    def __init__(self) -> None:
        self.requests: list[LlmRequest] = []

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        self.requests.append(request)
        return LlmResult("{}", model, 1.0, 10, 20)


def request(schema_name: str, effort: ReasoningEffort | None) -> LlmRequest:
    return LlmRequest(
        messages=(LlmMessage("user", "hello"),),
        max_output_tokens=256,
        temperature=0.0,
        reasoning_effort=effort,
        schema_name=schema_name,
    )


def test_default_policy_caps_every_mechanical_purpose_at_medium() -> None:
    policy = ReasoningEffortPolicy()
    assert policy.effort is DEFAULT_MECHANICAL_EFFORT is ReasoningEffort.MEDIUM
    for purpose in MECHANICAL_PURPOSES:
        assert policy.effort_for(purpose, ReasoningEffort.MAX) is ReasoningEffort.MEDIUM


@pytest.mark.parametrize("purpose", ANALYTICAL)
def test_analytical_purposes_keep_the_operators_effort(purpose: str) -> None:
    assert ReasoningEffortPolicy().effort_for(purpose, ReasoningEffort.MAX) is ReasoningEffort.MAX


def test_the_cap_never_raises_an_already_cheaper_choice() -> None:
    policy = ReasoningEffortPolicy()
    assert policy.effort_for("translation", ReasoningEffort.LOW) is ReasoningEffort.LOW
    assert policy.effort_for("translation", ReasoningEffort.NONE) is ReasoningEffort.NONE
    # No explicit effort means the provider default, which the cap must not replace.
    assert policy.effort_for("translation", None) is None


def test_an_inactive_policy_changes_nothing() -> None:
    policy = ReasoningEffortPolicy(None)
    assert not policy.active
    assert policy.effort_for("translation", ReasoningEffort.MAX) is ReasoningEffort.MAX


def test_the_purpose_set_is_configurable() -> None:
    policy = ReasoningEffortPolicy(ReasoningEffort.LOW, parse_mechanical_purposes("advocacy"))
    assert policy.effort_for("advocacy", ReasoningEffort.MAX) is ReasoningEffort.LOW
    assert policy.effort_for("translation", ReasoningEffort.MAX) is ReasoningEffort.MAX


def test_effort_and_purposes_parse_from_operator_text() -> None:
    assert parse_mechanical_effort(" HIGH ") is ReasoningEffort.HIGH
    assert parse_mechanical_effort("inherit") is None
    assert parse_mechanical_effort("") is None
    assert parse_mechanical_purposes("  ") == MECHANICAL_PURPOSES
    assert parse_mechanical_purposes("a_b, C") == frozenset({"a_b", "c"})
    with pytest.raises(ValueError, match="reasoning effort"):
        parse_mechanical_effort("enormous")
    with pytest.raises(ValueError, match="comma separated"):
        parse_mechanical_purposes("not a purpose!")


async def test_gateway_lowers_mechanical_effort_and_leaves_a_report_call_alone() -> None:
    inner = RecordingGateway()
    gateway = MechanicalEffortGateway(inner, ReasoningEffortPolicy())
    await gateway.complete(
        "https://model.test", "key", "gpt-5.6-luna", request("report", ReasoningEffort.MAX)
    )
    await gateway.complete(
        "https://model.test", "key", "gpt-5.6-luna", request("translation", ReasoningEffort.MAX)
    )
    assert [item.schema_name for item in inner.requests] == ["report", "translation"]
    assert inner.requests[0].reasoning_effort is ReasoningEffort.MAX
    assert inner.requests[1].reasoning_effort is ReasoningEffort.MEDIUM


async def test_gateway_preserves_every_other_request_field() -> None:
    inner = RecordingGateway()
    gateway = MechanicalEffortGateway(inner, ReasoningEffortPolicy())
    original = request("conflict_screening", ReasoningEffort.MAX)
    await gateway.complete("https://model.test", "key", "model", original)
    sent = inner.requests[0]
    assert sent is not original  # the caller's request object is never mutated
    assert original.reasoning_effort is ReasoningEffort.MAX
    assert (sent.messages, sent.max_output_tokens, sent.temperature) == (
        original.messages,
        original.max_output_tokens,
        original.temperature,
    )


def test_settings_expose_the_configured_policy_and_reject_nonsense() -> None:
    default = Settings(env="test").reasoning_effort_policy
    assert default.effort is ReasoningEffort.MEDIUM
    assert default.purposes == MECHANICAL_PURPOSES
    chosen = Settings(
        env="test", ai_mechanical_reasoning_effort="low", ai_mechanical_purposes="translation"
    ).reasoning_effort_policy
    assert chosen.effort is ReasoningEffort.LOW
    assert chosen.purposes == frozenset({"translation"})
    assert not Settings(
        env="test", ai_mechanical_reasoning_effort="inherit"
    ).reasoning_effort_policy.active
    with pytest.raises(ValueError, match="reasoning effort"):
        Settings(env="test", ai_mechanical_reasoning_effort="turbo")


def test_the_container_routes_every_provider_call_through_the_cap(container) -> None:
    gateway = container.llm
    assert isinstance(gateway, MechanicalEffortGateway)
    assert gateway.policy.effort is ReasoningEffort.MEDIUM
    # The same object serves reports, feed translation and administrator tests.
    assert gateway.apply(request("report", ReasoningEffort.MAX)).reasoning_effort is (
        ReasoningEffort.MAX
    )
    assert gateway.apply(request("connection_test", ReasoningEffort.MAX)).reasoning_effort is (
        ReasoningEffort.MEDIUM
    )
