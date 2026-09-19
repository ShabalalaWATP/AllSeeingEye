"""OpenAI-compatible completions, with native Responses for official OpenAI max reasoning.

The key travels only in the Authorization header. Provider errors contain a status only,
never response text, since callers persist them in report findings and usage records.
Responses must use identity encoding so HTTP decompression cannot allocate before the
streaming size guard. Local endpoints remain an administrator-controlled trust boundary.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import replace
from typing import Any

import httpx

from ase.adapters.llm.model_discovery import discover_models, model_id
from ase.adapters.llm.openai_responses import (
    RESPONSES_URL,
    build_responses_payload,
    parse_response,
    uses_responses,
)
from ase.application.ports.llm import LlmGatewayError, LlmGatewayTimeout
from ase.domain.ai_usage import token_count
from ase.domain.llm import LlmMessage, LlmRequest, LlmResult, normalise_base_url

DEFAULT_TIMEOUT_SECONDS = 120.0
MAX_REPORT_TIMEOUT_SECONDS = 300.0
#: Stages that reason before they answer. Cutting one off at the ordinary budget bills
#: the thinking and returns nothing, so they are given the longer one.
LONG_THINKING_SCHEMAS = frozenset(
    {
        "report",
        "report_topic",
        "report_synthesis",
        "report_judgements",
        "report_context",
        "conflict_screening",
        "report_alternatives",
        "report_collection",
        "report_analysis",
    }
)
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_CONCURRENT_REQUESTS = 2
MAX_JSON_DEPTH = 64


def completion_timeout_seconds(base_url: str, request: LlmRequest, override: float | None) -> float:
    """One total budget for admission, HTTP and parsing; explicit overrides win.

    A model asked to reason takes the longer budget on the stages that think, whichever
    API carries the call: the operator's Sol profile at high effort was cut off at the
    ordinary budget mid-synthesis, billed for the thinking and left the briefing paused.
    """
    if override is not None:
        return override
    if request.reasoning_effort is not None and request.schema_name in LONG_THINKING_SCHEMAS:
        return MAX_REPORT_TIMEOUT_SECONDS
    return DEFAULT_TIMEOUT_SECONDS


def _bounded_json(content: bytearray) -> Any:
    try:
        data = json.loads(content)
    except (ValueError, RecursionError):
        raise LlmGatewayError("The model endpoint returned invalid JSON.") from None
    pending = [(data, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > MAX_JSON_DEPTH:
            raise LlmGatewayError("The model endpoint returned invalid JSON.")
        if isinstance(value, dict):
            pending.extend(
                (child, depth + 1) for child in value.values() if isinstance(child, (dict, list))
            )
        elif isinstance(value, list):
            pending.extend((child, depth + 1) for child in value if isinstance(child, (dict, list)))
    return data


def _content(message: LlmMessage) -> str | list[dict[str, Any]]:
    if not message.images:
        return message.content
    return [{"type": "text", "text": message.content}] + [
        {
            "type": "image_url",
            "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(image.png).decode("ascii"),
                "detail": "high",
            },
        }
        for image in message.images
    ]


def build_payload(model: str, request: LlmRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": m.role, "content": _content(m)} for m in request.messages],
        "temperature": request.temperature,
        "max_tokens": request.max_output_tokens,
    }
    if request.reasoning_effort is not None or model == "gpt-5.6-luna":
        payload.pop("temperature")
        payload.pop("max_tokens")
        payload["max_completion_tokens"] = request.max_output_tokens
        if request.reasoning_effort is not None:
            payload["reasoning_effort"] = request.reasoning_effort
    if request.json_schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": request.schema_name,
                "schema": dict(request.json_schema),
                "strict": True,
            },
        }
    return payload


def parse_completion(data: Any, fallback_model: str, latency_ms: float) -> LlmResult:
    if not isinstance(data, dict):
        raise LlmGatewayError("The model endpoint returned something other than an object.")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise LlmGatewayError("The model endpoint returned no choices.")
    if choices[0].get("finish_reason") == "length":
        raise LlmGatewayError(
            "The model exhausted its completion token budget before finishing. "
            "Increase the token budget or reduce reasoning effort."
        )
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise LlmGatewayError("The model returned an empty message.")
    raw_usage = data.get("usage")
    usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    return LlmResult(
        content=content,
        model=model_id(data.get("model") or fallback_model),
        latency_ms=latency_ms,
        prompt_tokens=token_count(prompt),
        completion_tokens=token_count(completion),
    )


class OpenAiCompatibleGateway:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._timeout_override = timeout_seconds
        self._timeout = DEFAULT_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout), follow_redirects=False
        )
        self._admission = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_models(self, base_url: str, api_key: str) -> tuple[str, ...]:
        try:
            async with asyncio.timeout(min(self._timeout, 15)), self._admission:
                return await discover_models(self._client, base_url, api_key)
        except (TimeoutError, httpx.TimeoutException):
            raise LlmGatewayError("The model discovery endpoint timed out.") from None
        except httpx.HTTPError:
            raise LlmGatewayError("Could not reach the model discovery endpoint.") from None

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        try:
            base_url = normalise_base_url(base_url)
        except ValueError:
            raise LlmGatewayError("The model endpoint address is invalid.") from None
        headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
            "Authorization": f"Bearer {api_key}" if api_key else "",
        }
        started = time.perf_counter()
        native = uses_responses(base_url, request)
        timeout = completion_timeout_seconds(base_url, request, self._timeout_override)
        try:
            async with (
                asyncio.timeout(timeout),
                self._admission,
                self._client.stream(
                    "POST",
                    RESPONSES_URL if native else f"{base_url}/chat/completions",
                    json=build_responses_payload(model, request)
                    if native
                    else build_payload(model, request),
                    headers=headers,
                    auth=None,
                    timeout=timeout,
                    follow_redirects=False,
                ) as response,
            ):
                if response.status_code != 200:
                    if response.status_code in (400, 415, 422) and any(
                        message.images for message in request.messages
                    ):
                        raise LlmGatewayError(
                            "The configured model rejected image analysis or its structured "
                            "output settings. Ask an administrator to select a compatible "
                            "vision model; no alternative provider was used."
                        )
                    raise LlmGatewayError(f"The model endpoint answered {response.status_code}.")
                if response.headers.get("content-encoding", "identity").strip().lower() not in (
                    "",
                    "identity",
                ):
                    raise LlmGatewayError(
                        "The model endpoint returned unsupported compressed content."
                    )
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise LlmGatewayError(
                            "The model endpoint returned more than the allowed size."
                        )
                    content.extend(chunk)
        except (TimeoutError, httpx.TimeoutException):
            raise LlmGatewayTimeout("The model endpoint timed out.") from None
        except httpx.HTTPError as exc:
            raise LlmGatewayError(
                f"Could not reach the model endpoint: {type(exc).__name__}"
            ) from None
        data = _bounded_json(content)
        result = parse_response(data, model, 0) if native else parse_completion(data, model, 0)
        latency_ms = (time.perf_counter() - started) * 1000
        if latency_ms > timeout * 1000:
            raise LlmGatewayTimeout("The model endpoint timed out.")
        return replace(result, latency_ms=latency_ms)
