"""Provider gateway decorators for administrator controlled AI allowances."""

from __future__ import annotations

import asyncio
from uuid import UUID

from ase.application.ai_usage import AiUsageAccounting, settle_with_deadline
from ase.application.ports.llm import LlmGateway, LlmTokenBudgetExhausted
from ase.application.ports.web_search import WebSearchGateway, WebSearchRequest, WebSearchResult
from ase.application.report_jobs.budget import JobInterrupted
from ase.domain.llm import LlmRequest, LlmResult


class AllowanceLlmGateway:
    """Attribute one provider call to the current account and optional team."""

    def __init__(
        self,
        gateway: LlmGateway,
        accounting: AiUsageAccounting,
        *,
        owner_id: UUID,
        team_id: UUID | None,
        profile_id: UUID | None,
        purpose_prefix: str = "report",
    ) -> None:
        self._gateway = gateway
        self._accounting = accounting
        self._owner_id, self._team_id = owner_id, team_id
        self._profile_id, self._purpose_prefix = profile_id, purpose_prefix

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        batch = await self._accounting.reserve(
            self._owner_id,
            team_id=self._team_id,
            profile_id=self._profile_id,
            model=model,
            purpose=_purpose(self._purpose_prefix, request.schema_name),
            requested_tokens=_request_tokens(request),
        )
        result: LlmResult | None = None
        error: str | None = None
        try:
            result = await self._gateway.complete(base_url, api_key, model, request)
        except LlmTokenBudgetExhausted:
            error = "token_budget_exhausted"
            raise
        except asyncio.CancelledError:
            error = "cancelled"
            raise
        except Exception:
            error = "provider_error"
            raise
        finally:
            if batch is not None:
                settled = await settle_with_deadline(
                    self._accounting,
                    batch,
                    ok=error is None,
                    prompt_tokens=result.prompt_tokens if result else None,
                    completion_tokens=result.completion_tokens if result else None,
                    error=error,
                )
                if not settled and error is None:
                    raise JobInterrupted("AI allowance settlement could not be confirmed.")
        assert result is not None  # noqa: S101 - a successful provider call returns a result
        return result


class AllowanceWebSearchGateway:
    """Attribute native web discovery to the current account and optional team."""

    def __init__(
        self,
        gateway: WebSearchGateway,
        accounting: AiUsageAccounting,
        *,
        owner_id: UUID,
        team_id: UUID | None,
        profile_id: UUID | None,
    ) -> None:
        self._gateway = gateway
        self._accounting = accounting
        self._owner_id, self._team_id, self._profile_id = owner_id, team_id, profile_id

    async def search(self, api_key: str, model: str, request: WebSearchRequest) -> WebSearchResult:
        batch = await self._accounting.reserve(
            self._owner_id,
            team_id=self._team_id,
            profile_id=self._profile_id,
            model=model,
            purpose="report:web_search",
            requested_tokens=_text_tokens(request.query_context, request.max_output_tokens),
        )
        result: WebSearchResult | None = None
        error: str | None = None
        try:
            result = await self._gateway.search(api_key, model, request)
            if result.failure:
                error = "web_search_failed"
            return result
        except asyncio.CancelledError:
            error = "cancelled"
            raise
        except Exception:
            error = "provider_error"
            raise
        finally:
            if batch is not None:
                settled = await settle_with_deadline(
                    self._accounting,
                    batch,
                    ok=error is None,
                    prompt_tokens=result.prompt_tokens if result else None,
                    completion_tokens=result.completion_tokens if result else None,
                    error=error,
                )
                if not settled and error is None:
                    raise JobInterrupted("AI allowance settlement could not be confirmed.")


def _purpose(prefix: str, schema_name: str) -> str:
    return f"{prefix}:{schema_name}"[:64]


def _text_tokens(value: str, output_tokens: int) -> int:
    """Conservatively reserve input plus completion without trusting provider estimates."""
    input_tokens = min(32_000, max(1, (len(value) + 3) // 4))
    return output_tokens + input_tokens


def _request_tokens(request: LlmRequest) -> int:
    input_tokens = sum(
        min(32_000, max(1, (len(message.content) + 3) // 4)) + len(message.images) * 256
        for message in request.messages
    )
    return request.max_output_tokens + min(32_000, input_tokens)
