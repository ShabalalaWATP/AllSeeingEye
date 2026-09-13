"""Bounded source-backed answers with one unchanged, caller-selected model request."""

import asyncio
import json
from dataclasses import replace

import pytest

from ase.application.assistant.model import AssistantAnswerInvalid, answer_question
from ase.application.ports.llm import LlmGatewayError, LlmTokenBudgetExhausted
from ase.domain.assistant import (
    AssistantContext,
)
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmProvider, ReasoningEffort
from assistant_model_helpers import (
    CONTEXT,
    PROFILE,
    QUESTION,
    SOURCE,
    Cipher,
    Gateway,
    paragraph,
    response,
)
from test_model_schema_contracts import assert_strict_objects


@pytest.mark.parametrize(
    "provider,base,effort,budget",
    [
        (LlmProvider.OPENAI_COMPATIBLE, PROFILE.base_url, ReasoningEffort.MAX, 32000),
        (LlmProvider.OPENAI_COMPATIBLE, "http://localhost:1234/v1", None, 4096),
        (
            LlmProvider.BEDROCK,
            "https://bedrock-runtime.eu-west-2.amazonaws.com",
            ReasoningEffort.HIGH,
            9000,
        ),
    ],
)
async def test_one_call_preserves_profile_and_returns_server_references(
    provider, base, effort, budget
):
    gateway, cipher = (
        Gateway(response(paragraph("  An observation.  "), paragraph("Uncertain.", "gap", []))),
        Cipher(),
    )
    profile = replace(
        PROFILE, provider=provider, base_url=base, reasoning_effort=effort, max_output_tokens=budget
    )
    paragraphs, result = await answer_question(gateway, cipher, profile, QUESTION, CONTEXT)
    assert result is gateway.result
    assert [(p.kind, p.text, p.citations) for p in paragraphs] == [
        ("finding", "An observation.", ("E1",)),
        ("gap", "Uncertain.", ()),
    ]
    assert len(gateway.calls) == 1 and cipher.calls == [PROFILE.api_key_encrypted]
    url, key, model, request = gateway.calls[0]
    assert (url, key, model) == (base, "decrypted-test-marker", profile.model)
    assert (request.provider, request.reasoning_effort, request.max_output_tokens) == (
        provider,
        effort,
        budget,
    )
    assert request.temperature == profile.temperature and request.schema_name == "eye_assistant"
    assert [message.role for message in request.messages] == ["system", "user"]
    assert all(not message.images for message in request.messages)
    assert "decrypted-test-marker" not in repr(request)
    assert_strict_objects(request.json_schema)
    citations = request.json_schema["$defs"]["_Paragraph"]["properties"]["citations"]
    assert citations["items"]["pattern"] == r"^E[1-9][0-9]{0,3}$" and citations["maxItems"] == 8


@pytest.mark.parametrize(
    "content",
    [
        "",
        "[]",
        "null",
        "not json",
        '{"paragraphs": [], "paragraphs": []}',
        '{"paragraphs": NaN}',
        '{"paragraphs": [], "extra": true}',
        json.dumps({"paragraphs": []}),
        json.dumps({"paragraphs": [dict(paragraph(), extra=True)]}),
        response(paragraph(text=None)),
        response(paragraph(text=8)),
        response(paragraph(text=" ")),
        response(paragraph(kind="verified")),
        response(paragraph(citations="E1")),
        response(paragraph(citations=[1])),
        response(paragraph(citations=["E999"])),
        response(paragraph(citations=["E1", "E1"])),
        response(paragraph(citations=[])),
        response(paragraph(kind="inference", citations=[])),
        response(paragraph(text="x" * 2001)),
        response(*[paragraph()] * 11),
        response(*[paragraph(text="x" * 1800)] * 7),
        response(paragraph(text="private-output-marker\x00")),
        " " * (64 * 1024 + 1),
        "[" * 1500 + "]" * 1500,
        response(paragraph(citations=[f"E{x}" for x in range(1, 10)])),
    ],
    ids=[f"invalid-{index}" for index in range(26)],
)
async def test_invalid_output_is_rejected_once_and_keeps_only_usage_metadata(content):
    gateway = Gateway(content)
    with pytest.raises(AssistantAnswerInvalid) as caught:
        await answer_question(gateway, Cipher(), PROFILE, QUESTION, CONTEXT)
    error = caught.value
    assert len(gateway.calls) == 1
    assert str(error) == "The model returned an invalid or unsupported assistant answer."
    assert vars(error) == {
        "message": str(error),
        "fields": None,
        "model": "actual-model",
        "prompt_tokens": 80,
        "completion_tokens": 25,
        "latency_ms": 42,
    }
    assert "private-output-marker" not in str(error) + repr(vars(error))


@pytest.mark.parametrize(
    "text",
    [
        "https://example.org/path",
        "//example.org",
        "[source](relative/path)",
        "javascript:alert(1)",
        "data:text/plain,content",
        "file:///tmp/a",
        "mailto:person@example.org",
        '<img src="x">',
        "<script>untrusted</script>",
        "<svg/onload=alert(1)>",
        "<!--hidden-->",
        "&lt;iframe&gt;",
        "&amp;lt;script&amp;gt;",
        "https&#58;//example.org",
    ],
)
async def test_model_owned_links_and_html_are_rejected(text):
    with pytest.raises(AssistantAnswerInvalid):
        await answer_question(
            Gateway(response(paragraph(text))), Cipher(), PROFILE, QUESTION, CONTEXT
        )


async def test_domain_names_and_plain_text_reference_lookalikes_are_not_generated_links():
    text = "The record mentions bbc.co.uk and www.example.org; E999 is an unverified label."
    paragraphs, _ = await answer_question(
        Gateway(response(paragraph(text))), Cipher(), PROFILE, QUESTION, CONTEXT
    )
    assert paragraphs[0].text == text and paragraphs[0].citations == ("E1",)


async def test_numeric_claim_requires_value_in_cited_source():
    source = replace(SOURCE, title="Earthquake magnitude 4.5 in Japan")
    context = replace(CONTEXT, sources=(source,))
    supported, _ = await answer_question(
        Gateway(response(paragraph("The source reports magnitude 4.5."))),
        Cipher(),
        PROFILE,
        QUESTION,
        context,
    )
    assert supported[0].text.endswith("4.5.")
    with pytest.raises(AssistantAnswerInvalid):
        await answer_question(
            Gateway(response(paragraph("The source reports magnitude 7.2."))),
            Cipher(),
            PROFILE,
            QUESTION,
            context,
        )


async def test_empty_context_can_only_produce_an_uncited_gap():
    empty = AssistantContext((), 0, 0, False, ("No cached records matched this scope.",))
    paragraphs, _ = await answer_question(
        Gateway(response(paragraph("No evidence was supplied.", "gap", []))),
        Cipher(),
        PROFILE,
        QUESTION,
        empty,
    )
    assert paragraphs[0].kind == "gap" and not paragraphs[0].citations
    with pytest.raises(AssistantAnswerInvalid):
        await answer_question(Gateway(), Cipher(), PROFILE, QUESTION, empty)


async def test_exact_total_text_and_reference_limits_are_accepted():
    sources = tuple(replace(SOURCE, id=f"E{index}") for index in range(1, 9))
    gateway = Gateway(
        response(*[paragraph(text="x" * 2000, citations=[s.id for s in sources])] * 6)
    )
    paragraphs, _ = await answer_question(
        gateway, Cipher(), PROFILE, QUESTION, replace(CONTEXT, sources=sources)
    )
    assert sum(len(p.text) for p in paragraphs) == 12000 and len(paragraphs[0].citations) == 8


@pytest.mark.parametrize(
    "sources",
    [
        (SOURCE, SOURCE),
        (replace(SOURCE, id="https://example.org"),),
        (replace(SOURCE, id="E0"),),
        (replace(SOURCE, summary="x" * (256 * 1024)),),
    ],
)
async def test_invalid_or_oversized_input_stops_before_decrypting_or_calling(sources):
    gateway, cipher = Gateway(), Cipher()
    with pytest.raises(InvalidRequest):
        await answer_question(gateway, cipher, PROFILE, QUESTION, replace(CONTEXT, sources=sources))
    assert not gateway.calls and not cipher.calls


@pytest.mark.parametrize(
    "error",
    [
        LlmGatewayError("The provider is unavailable."),
        asyncio.CancelledError(),
        LlmTokenBudgetExhausted(model="selected-model", prompt_tokens=80, completion_tokens=32000),
    ],
)
async def test_provider_errors_and_cancellation_pass_through_without_retry(error):
    gateway = Gateway(error=error)
    with pytest.raises(type(error)) as caught:
        await answer_question(gateway, Cipher(), PROFILE, QUESTION, CONTEXT)
    assert caught.value is error and len(gateway.calls) == 1
