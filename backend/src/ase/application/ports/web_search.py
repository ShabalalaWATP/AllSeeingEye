"""Native provider web discovery, distinct from ordinary feed collection and drafting."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from ase.domain.llm import LlmUsage, ReasoningEffort
from ase.domain.web_research import WebCitation

WebSearchUsageSink = Callable[[LlmUsage], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class WebSearchRequest:
    query_context: str
    max_output_tokens: int
    reasoning_effort: ReasoningEffort | None


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    synthesis: str
    citations: tuple[WebCitation, ...]
    consulted_urls: tuple[str, ...]
    model: str
    tool_calls: int
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    failure: str | None = None


class WebSearchError(Exception):
    """Safe, fixed operator-facing message; never an upstream response body."""


class WebSearchGateway(Protocol):
    async def search(self, api_key: str, model: str, request: WebSearchRequest) -> WebSearchResult:
        """One Responses request, at most three tool calls; cancellation closes transport."""
        ...
