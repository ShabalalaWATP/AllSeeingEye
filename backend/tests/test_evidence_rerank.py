"""Embedding rerank reorders eligible evidence, and degrades honestly when absent."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.evidence_rerank import (
    FAILED,
    NO_CIPHER,
    NO_PROFILE,
    EvidenceReranker,
    candidate_text,
    rerank_note,
    rerank_query,
)
from ase.application.reports.selection import finish_selection, plan_selection
from ase.application.reports.templates import TEMPLATES
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.report_search import EmbeddingResult
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.source_provenance import SourceProfile
from feeds_helpers import NOW, make_event

PROFILES = {
    "wire": SourceProfile("wire", "wire-group", "Global Wire"),
    "paper": SourceProfile("paper", "paper-group", "The Daily Paper"),
    "local": SourceProfile("local", "local-group", "Local Herald"),
}
ACTOR = UUID(int=7)


class FakeCipher:
    available = True

    def decrypt(self, value: str) -> str:
        return "key"

    def encrypt(self, value: str) -> str:
        return value


class UnavailableCipher(FakeCipher):
    available = False


def prepared_profile(profile: LlmProfile | None):
    """The prepared routing answers for the embeddings role and reads nothing."""

    async def profile_for(role: LlmRole) -> LlmProfile | None:
        return profile if role is LlmRole.EMBEDDINGS else None

    return profile_for


class FakeEmbeddings:
    """Returns a unit vector per text, driven by a keyword the test controls."""

    def __init__(self, keyword: str, *, fail: bool = False) -> None:
        self.keyword = keyword
        self.fail = fail
        self.calls: list[list[str]] = []

    async def embed(self, base_url, api_key, model, texts):
        self.calls.append(list(texts))
        if self.fail:
            raise RuntimeError("endpoint down")
        vectors = tuple(
            (1.0, 0.0) if self.keyword in text.lower() else (0.0, 1.0) for text in texts
        )
        return EmbeddingResult(vectors, 12.0, 34)


def embeddings_profile() -> LlmProfile:
    return LlmProfile(
        id=uuid4(),
        name="Embeddings",
        base_url="http://localhost:11434/v1",
        model="test-embeddings",
        api_key_encrypted="secret",
        api_key_hint="cret",
        roles=frozenset({LlmRole.EMBEDDINGS}),
        max_output_tokens=64,
        temperature=0.0,
        enabled=True,
        created_at=datetime(2026, 9, 5, tzinfo=UTC),
        updated_at=datetime(2026, 9, 5, tzinfo=UTC),
    )


def pool():
    """Three distinct stories; only the third answers the stated requirement."""
    return [
        make_event("a", source_id="wire", title="Harvest yields rise across the plains"),
        make_event("b", source_id="paper", title="City council debates the tram budget"),
        make_event("c", source_id="local", title="Substation sabotage halts the grid"),
    ]


def make_plan(events):
    store = InMemoryEventStore()
    store.upsert(events)
    return plan_selection(
        store,
        replace(TEMPLATES["intsum"].strategy, max_items=3, per_source_cap=8),
        now=NOW,
    )


def reranker(gateway, *, cipher=None):
    return EvidenceReranker(cipher=cipher or FakeCipher(), gateway=gateway)


async def rank(gateway, plan, *, profile=True, **kwargs):
    return await reranker(gateway, **kwargs).rank(
        plan,
        profile_for=prepared_profile(embeddings_profile() if profile else None),
        question="What has disrupted electricity supply?",
        requirements=(IntelligenceRequirement("EEI-1", "Which substations were attacked?"),),
        actor_id=ACTOR,
        team_id=None,
        at=datetime(2026, 9, 5, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_similarity_reorders_eligible_items_without_admitting_new_ones():
    events = pool()
    plan = make_plan(events)
    gateway = FakeEmbeddings("substation")
    outcome = await rank(gateway, plan)
    assert outcome.reason == ""
    assert len(gateway.calls) == 1
    assert gateway.calls[0][0].startswith("What has disrupted electricity supply?")
    assert "Which substations were attacked?" in gateway.calls[0][0]
    plain = finish_selection(plan, PROFILES)
    reranked = finish_selection(plan, PROFILES, similarity=outcome.similarity)
    assert {item.event_id for item in plain.items} == {item.event_id for item in reranked.items}
    assert reranked.items[0].title == "Substation sabotage halts the grid"
    assert reranked.reranked == 3 and reranked.rerank_reason == ""


@pytest.mark.anyio
async def test_no_embeddings_profile_falls_back_with_a_recorded_reason():
    plan = make_plan(pool())
    gateway = FakeEmbeddings("substation")
    outcome = await rank(gateway, plan, profile=False)
    assert outcome.reason == NO_PROFILE and outcome.similarity == {}
    assert gateway.calls == []
    assert "no enabled embeddings profile" in rerank_note(outcome.reason)
    fallback = finish_selection(plan, PROFILES, rerank_reason=outcome.reason)
    assert [item.event_id for item in fallback.items] == [
        item.event_id for item in finish_selection(plan, PROFILES).items
    ]
    assert fallback.reranked == 0 and fallback.rerank_reason == NO_PROFILE


@pytest.mark.anyio
async def test_an_unavailable_cipher_never_reaches_the_endpoint():
    gateway = FakeEmbeddings("substation")
    outcome = await rank(gateway, make_plan(pool()), cipher=UnavailableCipher())
    assert outcome.reason == NO_CIPHER and gateway.calls == []


@pytest.mark.anyio
async def test_a_failed_endpoint_degrades_and_records_a_failed_call():
    plan = make_plan(pool())
    outcome = await rank(FakeEmbeddings("substation", fail=True), plan)
    assert outcome.reason == FAILED and outcome.similarity == {}
    assert outcome.usage is not None and outcome.usage.ok is False
    assert outcome.usage.purpose == "report:evidence_rerank"
    assert finish_selection(plan, PROFILES, rerank_reason=outcome.reason).rerank_reason == FAILED


@pytest.mark.anyio
async def test_a_successful_call_reports_its_metered_usage():
    outcome = await rank(FakeEmbeddings("substation"), make_plan(pool()))
    assert outcome.usage is not None
    assert outcome.usage.ok is True and outcome.usage.prompt_tokens == 34


@pytest.mark.anyio
async def test_an_empty_pool_asks_for_no_embedding():
    gateway = FakeEmbeddings("substation")
    outcome = await rank(gateway, make_plan([]))
    assert outcome.similarity == {} and gateway.calls == []


def test_the_rerank_query_and_candidate_text_stay_bounded():
    requirement = IntelligenceRequirement("EEI-1", "x" * 400)
    assert len(rerank_query("y" * 400, (requirement, requirement))) <= 1_200
    long_event = make_event("long", title="t" * 100, summary="s" * 4_000)
    assert len(candidate_text(long_event)) <= 1_200


def test_reranking_keeps_relevance_tiers_and_the_organisation_cap():
    events = [
        make_event("match", source_id="wire", title="Grid substation sabotage confirmed"),
        make_event("other", source_id="wire", title="Grid substation repairs continue"),
        make_event("off", source_id="paper", title="Unrelated harvest report"),
    ]
    store = InMemoryEventStore()
    store.upsert(events)
    plan = plan_selection(
        store,
        replace(TEMPLATES["intsum"].strategy, max_items=3, per_source_cap=1),
        now=NOW,
        term_groups=(("harvest",),),
    )
    # A large similarity on an unmatched item cannot beat the matched relevance tier.
    selected = finish_selection(plan, PROFILES, similarity={events[0].id: 1.0})
    assert selected.items[0].title == "Unrelated harvest report"
    assert sum(item.source_id == "wire" for item in selected.items) == 1
