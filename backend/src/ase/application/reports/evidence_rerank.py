"""Optional embedding rerank of the deterministic survivors, metered like every call.

The prefilter decides what is eligible; this only reorders eligible items by how close
they read to the question and its stated intelligence requirements. When no embeddings
profile is configured, or the endpoint fails, selection keeps today's deterministic
order and the report records why. Similarity is a retrieval signal: it never changes a
grade, admits an excluded item or stands in for corroboration.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from ase.application.ai_usage import AiUsageAccounting
from ase.application.ai_usage_gateway import AllowanceEmbeddingGateway
from ase.application.ports.embeddings import EmbeddingGateway
from ase.application.ports.llm import SecretCipher
from ase.application.reports.production_types import ProfileLookup
from ase.application.reports.selection import MAX_RERANK_CANDIDATES, SelectionPlan
from ase.domain.ai_usage import AiAllowanceExceeded, AiAttribution
from ase.domain.events import Event
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage
from ase.domain.report_search import checked_vector, cosine
from ase.domain.research_brief_values import IntelligenceRequirement

RERANK_TIMEOUT_SECONDS = 35
MAX_RERANK_TEXT_CHARS = 1_200
NO_PROFILE = "no_embeddings_profile"
NO_CIPHER = "encryption_unavailable"
NO_CANDIDATES = "no_candidates"
FAILED = "embeddings_call_failed"

RERANK_NOTES = {
    NO_PROFILE: (
        "Evidence was ordered by grade, recency and search terms only: no enabled "
        "embeddings profile is configured under Admin, Models."
    ),
    NO_CIPHER: (
        "Evidence was ordered by grade, recency and search terms only: the credential "
        "store is unavailable, so the embeddings profile could not be used."
    ),
    FAILED: (
        "Evidence was ordered by grade, recency and search terms only: the embeddings "
        "endpoint did not answer. No item was added, removed or regraded."
    ),
}


def rerank_note(reason: str) -> str:
    return RERANK_NOTES.get(reason, "")


@dataclass(frozen=True, slots=True)
class RerankOutcome:
    """The similarity map to apply, plus the reason when none could be produced."""

    similarity: dict[str, float] = field(default_factory=dict)
    reason: str = ""
    usage: LlmUsage | None = None


def rerank_query(question: str, requirements: Sequence[IntelligenceRequirement]) -> str:
    """The direction call's requirements steer the rerank, not the bare question."""
    parts = [question.strip(), *(row.question.strip() for row in requirements if row.question)]
    return " ".join(part for part in parts if part)[:MAX_RERANK_TEXT_CHARS]


def candidate_text(event: Event) -> str:
    title = event.title_en or event.title
    summary = (event.summary or "").strip()
    return f"{title}. {summary}"[:MAX_RERANK_TEXT_CHARS]


class EvidenceReranker:
    """Reorders the survivors of one job's prefilter with one bounded embedding call."""

    def __init__(
        self,
        *,
        cipher: SecretCipher,
        gateway: EmbeddingGateway,
        ai_usage: AiUsageAccounting | None = None,
        limit: int = MAX_RERANK_CANDIDATES,
    ) -> None:
        self._cipher = cipher
        self._gateway = gateway
        self._ai_usage = ai_usage
        self._limit = limit

    async def rank(
        self,
        plan: SelectionPlan,
        *,
        profile_for: ProfileLookup,
        question: str,
        requirements: Sequence[IntelligenceRequirement],
        actor_id: UUID,
        team_id: UUID | None,
        at: datetime,
    ) -> RerankOutcome:
        """Never raise for a missing capability; an exhausted AI allowance still stops work."""
        query = rerank_query(question, requirements)
        candidates = plan.rerank_candidates(self._limit) if query else ()
        if not candidates:
            return RerankOutcome(reason=NO_CANDIDATES)
        if not self._cipher.available:
            return RerankOutcome(reason=NO_CIPHER)
        # The prepared routing already chose this profile, so no read reopens here.
        profile = await profile_for(LlmRole.EMBEDDINGS)
        if profile is None:
            return RerankOutcome(reason=NO_PROFILE)
        return await self._embed(profile, query, candidates, actor_id, team_id, at)

    async def _embed(
        self,
        profile: LlmProfile,
        query: str,
        candidates: Sequence[Event],
        actor_id: UUID,
        team_id: UUID | None,
        at: datetime,
    ) -> RerankOutcome:
        texts = [query, *(candidate_text(event) for event in candidates)]
        gateway: EmbeddingGateway = self._gateway
        if self._ai_usage is not None:
            gateway = AllowanceEmbeddingGateway(
                gateway,
                self._ai_usage,
                attribution=AiAttribution.actor(actor_id, team_id),
                profile_id=profile.id,
                purpose="report:evidence_rerank",
            )
        started = time.perf_counter()
        try:
            key = self._cipher.decrypt(profile.api_key_encrypted)
            async with asyncio.timeout(RERANK_TIMEOUT_SECONDS):
                result = await gateway.embed(profile.base_url, key, profile.model, texts)
            vectors = tuple(checked_vector(vector) for vector in result.vectors)
            if len(vectors) != len(texts) or len({len(vector) for vector in vectors}) != 1:
                raise ValueError("Invalid vectors.")
        except AiAllowanceExceeded:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            # The safe message is fixed text: no endpoint body or credential is echoed.
            return RerankOutcome(
                reason=FAILED,
                usage=self._usage(profile, actor_id, at, started, ok=False),
            )
        similarity = {
            event.id: cosine(vectors[0], vector)
            for event, vector in zip(candidates, vectors[1:], strict=True)
        }
        return RerankOutcome(
            similarity=similarity,
            usage=self._usage(
                profile,
                actor_id,
                at,
                started,
                ok=True,
                prompt_tokens=result.prompt_tokens,
                latency_ms=result.latency_ms,
            ),
        )

    def _usage(
        self,
        profile: LlmProfile,
        actor_id: UUID,
        at: datetime,
        started: float,
        *,
        ok: bool,
        prompt_tokens: int | None = None,
        latency_ms: float | None = None,
    ) -> LlmUsage:
        return LlmUsage(
            at=at,
            profile_id=profile.id,
            user_id=actor_id,
            purpose="report:evidence_rerank",
            ok=ok,
            latency_ms=(
                latency_ms if latency_ms is not None else (time.perf_counter() - started) * 1000
            ),
            prompt_tokens=prompt_tokens,
            error=None if ok else RERANK_NOTES[FAILED][:500],
        )
