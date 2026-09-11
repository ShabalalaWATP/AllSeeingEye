"""Keep provider requests unchanged while enforcing the report's durable allowance."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from ase.application.ports.llm import LlmGateway
from ase.application.ports.web_search import WebSearchGateway, WebSearchRequest, WebSearchResult
from ase.application.report_jobs.budget import ReportCallBudget
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmRequest, LlmResult


def _hash_request(values: Mapping[str, Any]) -> str:
    try:
        canonical = json.dumps(values, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise InvalidRequest("The report model request could not be fingerprinted.") from None
    return hashlib.sha256(canonical.encode()).hexdigest()


class BudgetedLlmGateway:
    def __init__(self, gateway: LlmGateway, budget: ReportCallBudget) -> None:
        self._gateway, self._budget = gateway, budget

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        request_hash = _hash_request(
            {
                "kind": "completion",
                "endpoint": base_url,
                "model": model,
                "provider": request.provider,
                "effort": request.reasoning_effort,
                "output": request.max_output_tokens,
                "temperature": request.temperature,
                "schema": request.json_schema,
                "schema_name": request.schema_name,
                "messages": [
                    {
                        "role": message.role,
                        "content": message.content,
                        "images": [
                            hashlib.sha256(image.png).hexdigest() for image in message.images
                        ],
                    }
                    for message in request.messages
                ],
            }
        )
        return await self._budget.run(
            request_hash=request_hash,
            schema=request.schema_name,
            model=model,
            reserved_output=request.max_output_tokens,
            invoke=lambda: self._gateway.complete(base_url, api_key, model, request),
        )


class BudgetedWebSearchGateway:
    def __init__(self, gateway: WebSearchGateway, budget: ReportCallBudget) -> None:
        self._gateway, self._budget = gateway, budget

    async def search(self, api_key: str, model: str, request: WebSearchRequest) -> WebSearchResult:
        request_hash = _hash_request(
            {
                "kind": "web_search",
                "model": model,
                "query": request.query_context,
                "output": request.max_output_tokens,
                "effort": request.reasoning_effort,
            }
        )
        return await self._budget.run(
            request_hash=request_hash,
            schema="web_search",
            model=model,
            reserved_output=request.max_output_tokens,
            invoke=lambda: self._gateway.search(api_key, model, request),
        )
