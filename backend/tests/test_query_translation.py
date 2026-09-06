"""Generated query variants remain aligned, bounded and untrusted."""

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ase.application.ports.llm import LlmGatewayError
from ase.application.research.query_translation import parse_translation, translate_queries
from ase.domain.llm import LlmProfile, LlmResult, LlmRole

TERMS = ('"Acme" project 1234',)
LANGUAGES = ("fa", "zh-Hant")


def content() -> str:
    return json.dumps(
        {
            "variants": [
                {"language": "fa", "terms": ['پروژه "Acme" 1234']},
                {"language": "zh-Hant", "terms": ['"Acme" 項目 1234']},
            ]
        }
    )


class Gateway:
    def __init__(self, body: str = "", error: Exception | None = None) -> None:
        self.body, self.error = body, error
        self.calls = 0

    async def complete(self, *args):
        self.calls += 1
        if self.error:
            raise self.error
        return LlmResult(self.body, "fixture", 10, 20, 30)


def profile() -> LlmProfile:
    now = datetime.now(UTC)
    return LlmProfile(
        uuid4(),
        "Test",
        "https://example.test",
        "fixture",
        "cipher",
        "hint",
        frozenset({LlmRole.TRANSLATION}),
        3000,
        0,
        True,
        now,
        now,
    )


async def test_one_call_retains_originals_and_usage() -> None:
    gateway = Gateway(content())
    result = await translate_queries(gateway, profile(), "", TERMS, LANGUAGES)
    assert result.original_terms == TERMS and result.model == "fixture"
    assert result.variants[0].terms == ('پروژه "Acme" 1234',)
    assert result.variants[1].language == "zh-Hant"
    assert result.prompt_tokens == 20 and result.completion_tokens == 30
    assert gateway.calls == 1 and not result.findings


@pytest.mark.parametrize(
    "bad",
    [
        "{}",
        "[]",
        "not json",
        '{"variants":[]}',
        '{"variants":[null,null]}',
        content().replace("1234", "9999"),
        content().replace("1234", "12345"),
        content().replace("1234", "1234 9999"),
        content().replace("Acme", "Other"),
        content().replace("zh-Hant", "zh-Hans"),
        content().replace('"terms": [', '"terms": [42,'),
        content().replace('"variants":', '"extra":1,"variants":'),
        pytest.param(" " * 40_001, id="oversized"),
    ],
)
async def test_invalid_output_falls_back_without_echoing_private_text(bad: str) -> None:
    result = await translate_queries(Gateway(bad), profile(), "", TERMS, LANGUAGES)
    assert not result.variants and result.findings
    assert "Acme" not in result.findings[0].message
    assert result.prompt_tokens == 20


@pytest.mark.parametrize("languages", [(), ("fa", "fa"), ("zz",), ("en",) * 9])
async def test_bad_inputs_do_not_call_model(languages: tuple[str, ...]) -> None:
    gateway = Gateway()
    with pytest.raises(ValueError):
        await translate_queries(gateway, profile(), "", TERMS, languages)
    assert gateway.calls == 0


@pytest.mark.parametrize("error", [LlmGatewayError("sensitive upstream data"), TimeoutError()])
async def test_failure_has_no_retry_or_error_disclosure(error: Exception) -> None:
    gateway = Gateway(error=error)
    result = await translate_queries(gateway, profile(), "", TERMS, LANGUAGES)
    assert gateway.calls == 1 and not result.variants
    assert "sensitive" not in result.findings[0].message


async def test_cancellation_is_not_converted_into_success() -> None:
    class Cancelled:
        async def complete(self, *args):
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await translate_queries(Cancelled(), profile(), "", TERMS, LANGUAGES)


def test_parser_rejects_controls_and_overlong_terms() -> None:
    for term in ['"Acme" 1234\n', '"Acme" 1234' + "x" * 301]:
        payload = json.dumps({"variants": [{"language": "fa", "terms": [term]}]})
        with pytest.raises(ValueError):
            parse_translation(payload, TERMS, ("fa",))
