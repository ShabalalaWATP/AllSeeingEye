"""Bedrock rejects unsafe streams early and retains local report validation."""

from collections.abc import AsyncIterator
from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from ase.adapters.llm import bedrock
from ase.adapters.llm.bedrock import BedrockConverseGateway
from ase.adapters.llm.bedrock_schema import project_schema
from ase.adapters.llm.translator import parse_translations, translation_request
from ase.application.ports.llm import LlmGatewayError
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.report_input import parse_model_body
from ase.domain.report_schema import REPORT_BODY_SCHEMA
from ase.domain.reports import MAX_JUDGEMENT_CHARS, ReportParseError
from report_helpers import good_body
from test_bedrock_gateway import BASE, MODEL, REQUEST


class Stream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.read = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for _ in range(3):
            self.read += 1
            yield b" " * 16

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize("kind", ["redirect", "gzip", "size"])
async def test_rejected_streams_are_closed_without_reading_unnecessary_content(
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = Stream()
    monkeypatch.setattr(bedrock, "MAX_RESPONSE_BYTES", 16)

    def handler(request: httpx.Request) -> httpx.Response:
        if kind == "redirect":
            return httpx.Response(302, headers={"Location": "https://wrong.invalid"}, stream=stream)
        headers = {"Content-Encoding": "gzip"} if kind == "gzip" else {}
        return httpx.Response(200, headers=headers, stream=stream)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        with pytest.raises(LlmGatewayError):
            await BedrockConverseGateway(client=client).complete(
                BASE, "fixture-key", MODEL, REQUEST
            )
    assert stream.read == (2 if kind == "size" else 0)
    assert stream.closed


async def test_transport_exception_never_echoes_key_or_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("key=fixture-key private-query", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LlmGatewayError) as error:
            await BedrockConverseGateway(client=client).complete(
                BASE, "fixture-key", MODEL, REQUEST
            )
    assert str(error.value) == "Could not reach Bedrock."


def test_outbound_projection_does_not_remove_local_report_length_validation() -> None:
    project_schema(REPORT_BODY_SCHEMA)
    body = good_body(
        key_judgements=[
            {
                **good_body()["key_judgements"][0],
                "statement": "x" * (MAX_JUDGEMENT_CHARS + 1),
            }
        ]
    )
    with pytest.raises(ReportParseError):
        parse_model_body(body)


def test_translation_count_constraints_stay_local_after_schema_projection() -> None:
    now = datetime.now(UTC)
    profile = LlmProfile(
        uuid4(),
        "fixture",
        BASE,
        MODEL,
        "",
        "",
        frozenset({LlmRole.TRANSLATION}),
        2000,
        0,
        True,
        now,
        now,
    )
    request = translation_request([("Bonjour", "fr"), ("Salut", "fr")], profile)
    original = deepcopy(request.json_schema)
    assert original is not None
    projected = project_schema(original)
    assert "minItems" not in projected["properties"]["translations"]
    assert "maxItems" not in projected["properties"]["translations"]
    assert request.json_schema == original
    with pytest.raises(ValueError, match="count"):
        parse_translations('{"translations":["Hello"]}', 2)
