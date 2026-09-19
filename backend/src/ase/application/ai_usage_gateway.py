"""Provider gateway decorators for administrator controlled AI allowances.

Wrap the provider gateway directly, so the only work between reservation and the
provider request is recording dispatch.  Outcomes are classified explicitly:

* an exception before the inner call (cancellation while reserving or recording
  dispatch) releases the reservation;
* an answer settles its reported usage, conservatively charging the reservation when a
  completed call reports no counts;
* a provider error counts the request with only the tokens it reported, usually zero;
* a timeout or cancellation after dispatch is held as unknown for review.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from uuid import UUID

from ase.application.ai_usage import (
    SETTLEMENT_SECONDS,
    AiUsageAccounting,
    finish_with_deadline,
)
from ase.application.ports.embeddings import EmbeddingGateway
from ase.application.ports.llm import LlmGateway, LlmGatewayTimeout, LlmTokenBudgetExhausted
from ase.application.ports.web_search import (
    WebSearchGateway,
    WebSearchRequest,
    WebSearchResult,
    WebSearchTimeout,
)
from ase.application.report_jobs.budget import CallNotDispatched, JobInterrupted
from ase.domain.ai_usage import MAX_ALLOWANCE, AiAttribution, AiCallOutcome
from ase.domain.llm import LlmRequest, LlmResult
from ase.domain.report_search import EmbeddingResult

Usage = tuple[int | None, int | None, str | None]


async def metered_call[Result](
    accounting: AiUsageAccounting,
    attribution: AiAttribution,
    *,
    profile_id: UUID | None,
    model: str,
    purpose: str,
    requested_tokens: int,
    call: Callable[[], Awaitable[Result]],
    usage_of: Callable[[Result], Usage],
) -> tuple[Result, bool]:
    """Run one provider call under the allowance ledger; return whether it settled."""
    batch = await accounting.reserve(
        attribution,
        profile_id=profile_id,
        model=model,
        purpose=purpose,
        requested_tokens=requested_tokens,
    )
    try:
        async with asyncio.timeout(SETTLEMENT_SECONDS):
            await accounting.mark_dispatched(batch)
    except asyncio.CancelledError:
        await finish_with_deadline(accounting, batch, AiCallOutcome.NOT_DISPATCHED)
        raise
    except Exception:
        await finish_with_deadline(accounting, batch, AiCallOutcome.NOT_DISPATCHED)
        raise CallNotDispatched("AI allowance dispatch could not be recorded.") from None
    outcome, prompt, completion = AiCallOutcome.UNKNOWN, None, None
    error: str | None = "interrupted"
    try:
        result = await call()
        prompt, completion, error = usage_of(result)
        outcome = AiCallOutcome.FAILED if error else AiCallOutcome.COMPLETED
    except LlmTokenBudgetExhausted as exc:
        outcome, error = AiCallOutcome.FAILED, "token_budget_exhausted"
        prompt, completion = exc.prompt_tokens, exc.completion_tokens
        raise
    except (LlmGatewayTimeout, WebSearchTimeout, TimeoutError):
        outcome, error = AiCallOutcome.UNKNOWN, "timeout"
        raise
    except asyncio.CancelledError:
        outcome, error = AiCallOutcome.UNKNOWN, "cancelled"
        raise
    except Exception:
        outcome, error = AiCallOutcome.FAILED, "provider_error"
        raise
    finally:
        settled = await finish_with_deadline(
            accounting,
            batch,
            outcome,
            prompt_tokens=prompt,
            completion_tokens=completion,
            error=error,
        )
    return result, settled


class AllowanceLlmGateway:
    """Attribute each provider call to an account (optionally for a team) or the system."""

    def __init__(
        self,
        gateway: LlmGateway,
        accounting: AiUsageAccounting,
        *,
        attribution: AiAttribution,
        profile_id: UUID | None,
        purpose_prefix: str = "report",
        strict: bool = True,
    ) -> None:
        self._gateway, self._accounting = gateway, accounting
        self._attribution, self._profile_id = attribution, profile_id
        self._purpose_prefix, self._strict = purpose_prefix, strict
        self.settlement_confirmed = True

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        result, settled = await metered_call(
            self._accounting,
            self._attribution,
            profile_id=self._profile_id,
            model=model,
            purpose=_purpose(self._purpose_prefix, request.schema_name),
            requested_tokens=_request_tokens(request),
            call=lambda: self._gateway.complete(base_url, api_key, model, request),
            usage_of=lambda value: (value.prompt_tokens, value.completion_tokens, None),
        )
        self.settlement_confirmed = settled
        if not settled and self._strict:
            raise JobInterrupted("AI allowance settlement could not be confirmed.")
        return result


class AllowanceWebSearchGateway:
    """Attribute native web discovery to the current account and optional team."""

    def __init__(
        self,
        gateway: WebSearchGateway,
        accounting: AiUsageAccounting,
        *,
        attribution: AiAttribution,
        profile_id: UUID | None,
    ) -> None:
        self._gateway, self._accounting = gateway, accounting
        self._attribution, self._profile_id = attribution, profile_id

    async def search(self, api_key: str, model: str, request: WebSearchRequest) -> WebSearchResult:
        result, settled = await metered_call(
            self._accounting,
            self._attribution,
            profile_id=self._profile_id,
            model=model,
            purpose="report:web_search",
            requested_tokens=_text_tokens(request.query_context, request.max_output_tokens),
            call=lambda: self._gateway.search(api_key, model, request),
            usage_of=_web_usage,
        )
        if not settled:
            raise JobInterrupted("AI allowance settlement could not be confirmed.")
        return result


class AllowanceEmbeddingGateway:
    """Attribute embedding requests; they report prompt tokens only."""

    def __init__(
        self,
        gateway: EmbeddingGateway,
        accounting: AiUsageAccounting,
        *,
        attribution: AiAttribution,
        profile_id: UUID | None,
        purpose: str = "embeddings",
    ) -> None:
        self._gateway, self._accounting = gateway, accounting
        self._attribution, self._profile_id, self._purpose = attribution, profile_id, purpose

    async def embed(
        self, base_url: str, api_key: str, model: str, texts: Sequence[str]
    ) -> EmbeddingResult:
        result, _settled = await metered_call(
            self._accounting,
            self._attribution,
            profile_id=self._profile_id,
            model=model,
            purpose=self._purpose,
            requested_tokens=min(
                1_000_000, sum(max(1, (len(text) + 3) // 4) for text in texts) or 1
            ),
            call=lambda: self._gateway.embed(base_url, api_key, model, texts),
            # Embeddings have no completion; zero is the exact completion count.
            usage_of=lambda value: (value.prompt_tokens, 0, None),
        )
        return result


def _web_usage(result: WebSearchResult) -> Usage:
    return (
        result.prompt_tokens,
        result.completion_tokens,
        ("web_search_failed" if result.failure else None),
    )


def _purpose(prefix: str, schema_name: str) -> str:
    """An empty prefix lets a single-purpose consumer record its own exact purpose."""
    return (f"{prefix}:{schema_name}" if prefix else schema_name)[:64]


def _text_tokens(value: str, output_tokens: int) -> int:
    """Conservatively reserve input plus completion without trusting provider estimates."""
    input_tokens = max(1, len(value.encode("utf-8")))
    return min(MAX_ALLOWANCE, output_tokens + input_tokens)


def _request_tokens(request: LlmRequest) -> int:
    input_tokens = sum(
        max(1, len(message.content.encode("utf-8")))
        + sum(max(256, len(image.png)) for image in message.images)
        for message in request.messages
    )
    return min(MAX_ALLOWANCE, request.max_output_tokens + input_tokens)
