"""Destination routing, private-input exclusion, source controls and frozen web provenance."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from ase.adapters.llm.openai_web_search import OpenAiWebSearchGateway
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.application.ports.web_search import WebSearchError
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.production_collection import prepare_collection
from ase.application.reports.production_types import Totals
from ase.application.reports.research_export import research_sections
from ase.application.reports.web_research_export import web_context_markdown
from ase.application.research.service import ResearchCollectionService
from ase.domain.errors import EncryptionUnavailable
from ase.domain.llm import LlmProvider, LlmRole
from ase.domain.research import ResearchFocus
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from ase.domain.web_research import WEB_SOURCE_ID, WebCitation, WebResearchRecord, public_web_url
from ase.infrastructure.rate_limit import InMemorySlidingWindowLimiter
from helpers import FakeClock
from web_search_helpers import (
    CITATION,
    NOW,
    QUERY,
    RESULT,
    TEXT,
    URL,
    Admission,
    Cipher,
    Gateway,
    job,
    native_response,
    profile,
)


def setup(gateway=None, admission=None, selected=None):
    clock = FakeClock(NOW)
    gateway, admission = gateway or Gateway(), admission or Admission()
    service = FreshWebResearch(gateway, admission, clock, InMemorySlidingWindowLimiter(clock))
    selected = selected or profile()
    roles = []

    async def lookup(role):
        roles.append(role)
        return selected

    return service, gateway, admission, lookup, roles


async def test_uses_destination_direction_profile_and_discloses_only_public_query_scope():
    selected = profile()
    service, gateway, admission, lookup, roles = setup(selected=selected)
    totals = Totals()
    query = replace(QUERY, country_isos=("GB", "DE"), languages=("en", "de"))
    result = await service.collect(job(), query, totals, Cipher(), lookup)
    assert result.status == "completed" and result.synthesis == TEXT
    assert result.profile_id == selected.id and result.profile_revision == 3
    assert (
        result.requested_model == "configured-model" and result.returned_model == "returned-model"
    )
    assert roles == [LlmRole.DIRECTION]
    key, model, request = gateway.calls[0]
    assert key == "fixture-native-key" and model == "configured-model"
    assert request.max_output_tokens == 8000 and request.reasoning_effort == "max"
    context = json.loads(request.query_context)
    assert (
        context["countries"] == ["GB", "DE"]
        and context["since_inclusive"] == query.since.isoformat()
    )
    assert "encrypted" not in request.query_context and "seed_events" not in context
    assert set(admission.seen) == {WEB_SOURCE_ID}
    assert totals.usage[0].ok and totals.prompt_tokens == 30 and totals.completion_tokens == 15


@pytest.mark.parametrize(
    ("model", "effort", "configured", "expected"),
    [
        ("configured-model", None, 8000, 6000),
        ("configured-model", None, 2048, 2048),
        ("configured-model", "max", 2048, 2048),
        ("configured-model", "max", 8000, 8000),
        ("gpt-5.6-luna", "max", 16000, 16000),
        ("gpt-5.6-luna", None, 16000, 16000),
        ("gpt-5.6-luna", "max", 32000, 16000),
    ],
)
async def test_web_budget_preserves_profile_limits_and_reasoning_headroom(
    model, effort, configured, expected
):
    selected = profile(model=model, reasoning_effort=effort, max_output_tokens=configured)
    service, gateway, _, lookup, _ = setup(selected=selected)
    record = await service.collect(job(), QUERY, Totals(), Cipher(), lookup)
    assert record.status == "completed" and len(gateway.calls) == 1
    _, sent_model, request = gateway.calls[0]
    assert sent_model == model and request.reasoning_effort == effort
    assert request.max_output_tokens == expected
    assert f"{expected:,} output tokens" in record.explanation


async def test_incomplete_reasoning_search_keeps_billable_usage_without_retry_or_context():
    calls = []

    def handler(request):
        calls.append(request)
        payload = json.loads(request.content)
        assert payload["max_output_tokens"] == 16000 and payload["max_tool_calls"] == 3
        return httpx.Response(
            200,
            json=native_response(
                status="incomplete", usage={"input_tokens": 900, "output_tokens": 16000}
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service, _, _, lookup, _ = setup(
            gateway=OpenAiWebSearchGateway(client=client),
            selected=profile(model="gpt-5.6-luna", max_output_tokens=16000),
        )
        totals = Totals()
        record = await service.collect(job(), QUERY, totals, Cipher(), lookup)
    assert len(calls) == record.request_count == len(totals.usage) == 1
    assert record.status == "failed" and not totals.usage[0].ok
    assert not record.synthesis and not record.citations and not record.consulted_urls
    assert record.completion_tokens == totals.completion_tokens == 16000
    assert record.prompt_tokens == totals.prompt_tokens == 900


@pytest.mark.parametrize("change", ["off", "document", "media", "disabled"])
async def test_no_query_or_profile_disclosure_without_eligible_explicit_search(change):
    service, gateway, admission, lookup, roles = setup()
    query = QUERY
    if change == "off":
        query = replace(query, research_web_search=False)
    elif change in {"document", "media"}:
        query = replace(query, focus=ResearchFocus(change))
    else:
        admission.active = False
    record = await service.collect(job(), query, Totals(), Cipher(), lookup)
    assert record.status != "completed" and record.request_count == 0
    assert not gateway.calls and not roles


@pytest.mark.parametrize(
    "selected",
    [
        profile(base_url="http://localhost:11434/v1"),
        profile(base_url="https://api.openai.com.evil.example/v1"),
        profile(provider=LlmProvider.BEDROCK),
        profile(enabled=False),
    ],
)
async def test_no_fallback_when_destination_provider_is_unsupported(selected):
    service, gateway, _, lookup, roles = setup(selected=selected)
    record = await service.collect(job(), QUERY, Totals(), Cipher(), lookup)
    assert record.status == "unsupported" and record.profile_id == selected.id
    assert not gateway.calls and roles == [LlmRole.DIRECTION]


async def test_missing_profile_and_unavailable_cipher_never_dispatch():
    service, gateway, _, _, _ = setup()

    async def missing(_):
        return None

    result = await service.collect(job(), QUERY, Totals(), Cipher(), missing)
    assert result.status == "unavailable" and result.request_count == 0

    class BrokenCipher:
        def decrypt(self, _):
            raise EncryptionUnavailable()

    selected = profile()

    async def lookup(_):
        return selected

    result = await service.collect(job(), QUERY, Totals(), BrokenCipher(), lookup)
    assert result.status == "unavailable" and not gateway.calls


async def test_disable_during_fetch_withholds_context_but_keeps_attempt_usage():
    admission = Admission()
    gateway = Gateway(after=lambda: setattr(admission, "active", False))
    service, _, _, lookup, _ = setup(gateway=gateway, admission=admission)
    totals = Totals()
    result = await service.collect(job(), QUERY, totals, Cipher(), lookup)
    assert result.status == "unavailable" and not result.synthesis
    assert not result.citations and not result.consulted_urls
    assert result.request_count == 1 and result.prompt_tokens == 30
    assert len(totals.usage) == 1 and totals.usage[0].ok is False


async def test_user_rate_limit_bounds_search_attempts():
    service, gateway, _, lookup, _ = setup()
    actor_job = job()
    for _ in range(6):
        result = await service.collect(actor_job, QUERY, Totals(), Cipher(), lookup)
        assert result.status == "completed"
    result = await service.collect(actor_job, QUERY, Totals(), Cipher(), lookup)
    assert result.status == "unavailable" and "rate limit" in result.explanation
    assert len(gateway.calls) == 6


async def test_failure_and_cancelled_call_record_unknown_usage_without_generated_content():
    service, _, _, lookup, _ = setup(gateway=Gateway(WebSearchError("Safe failure")))
    totals = Totals()
    result = await service.collect(job(), QUERY, totals, Cipher(), lookup)
    assert result.status == "failed" and not result.synthesis
    assert totals.usage[0].prompt_tokens is None and totals.findings
    gateway = Gateway()
    gateway.hold = True
    service, _, _, lookup, _ = setup(gateway=gateway)
    totals = Totals()
    task = asyncio.create_task(service.collect(job(), QUERY, totals, Cipher(), lookup))
    await gateway.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert gateway.cancelled and len(totals.usage) == 1
    assert totals.usage[0].error == "The web search was cancelled; final provider usage is unknown."


async def test_production_collection_preserves_generated_context_outside_evidence_pool():
    service, gateway, _, lookup, _ = setup()
    totals = Totals()
    actor_job = job()
    store, receipt, query = await prepare_collection(
        actor_job,
        None,
        totals,
        ResearchCollectionService(lambda _: ()),
        InMemoryEventStore,
        InMemoryEventStore(),
        None,
        cipher=Cipher(),
        profile_for=lookup,
        web_research=service,
    )
    assert receipt.web_research.synthesis == TEXT
    assert query.research_web_search and len(gateway.calls) == 1
    assert receipt.collected_items == 0 and store.query(EventQuery()) == []
    assert "Do not cite it as E-labelled evidence" in receipt.describe()
    frozen = research_from_dict(research_to_dict(receipt))
    assert frozen == receipt
    assert "published_at" not in json.dumps(research_to_dict(receipt)["web_research"])
    sections = dict(research_sections(receipt))
    assert URL in "\n".join(sections["Fresh web context"])
    markdown = "\n".join(web_context_markdown(receipt.web_research))
    assert "[Climate report](https://example.org/climate-report)" in markdown
    assert "AI-generated web context" in markdown


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///secret",
        "http://localhost/a",
        "http://127.0.0.1/a",
        "http://127.1/a",
        "http://0x7f.0.0.1/a",
        "https://user:pass@example.org",
        "https://example.org/a%0Ab",
        "https://example.org:8001/path",
        "https://host.internal/path",
    ],
)
def test_provider_reference_links_reject_nonpublic_and_unsafe_destinations(url):
    assert not public_web_url(url)
    with pytest.raises(ValueError):
        WebCitation(url, "Unsafe", 0, 1)


def test_completed_and_unsuccessful_records_cannot_lie_about_execution_or_provenance():
    with pytest.raises(ValueError, match="executed search"):
        WebResearchRecord("completed", "", NOW, synthesis=TEXT, citations=(CITATION,))
    with pytest.raises(ValueError, match="cannot release"):
        WebResearchRecord("failed", "", NOW, synthesis=TEXT)
    original = ResearchReceipt.build(QUERY, (), 0)
    assert "web_research" not in research_to_dict(original)
    assert research_from_dict(research_to_dict(original)) == original
    assert RESULT.tool_calls == 1
