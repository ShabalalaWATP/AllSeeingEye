"""Chat completions against any OpenAI-compatible endpoint (OpenAI, Ollama, LM Studio, vLLM).

The key travels only in the Authorization header; errors quote the status and at most a
short, redacted excerpt of the body so a misconfigured endpoint can be diagnosed
without the key or the prompt ever reaching a log.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from ase.application.ports.llm import LlmGatewayError
from ase.domain.llm import LlmRequest, LlmResult

DEFAULT_TIMEOUT_SECONDS = 120.0
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
ERROR_EXCERPT_CHARS = 200


def _excerpt(text: str) -> str:
    flat = " ".join(text.split())
    return flat[:ERROR_EXCERPT_CHARS]


def build_payload(model: str, request: LlmRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        "temperature": request.temperature,
        "max_tokens": request.max_output_tokens,
    }
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
        model=str(data.get("model") or fallback_model),
        latency_ms=latency_ms,
        prompt_tokens=prompt if isinstance(prompt, int) else None,
        completion_tokens=completion if isinstance(completion, int) else None,
    )


class OpenAiCompatibleGateway:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        started = time.perf_counter()
        try:
            response = await self._client.post(
                f"{base_url}/chat/completions", json=build_payload(model, request), headers=headers
            )
        except httpx.HTTPError as exc:
            raise LlmGatewayError(
                f"Could not reach the model endpoint: {type(exc).__name__}"
            ) from exc
        latency_ms = (time.perf_counter() - started) * 1000
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise LlmGatewayError("The model endpoint returned more than the allowed size.")
        if response.status_code >= 400:
            raise LlmGatewayError(
                f"The model endpoint answered {response.status_code}: {_excerpt(response.text)}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise LlmGatewayError("The model endpoint returned invalid JSON.") from exc
        return parse_completion(data, model, latency_ms)
