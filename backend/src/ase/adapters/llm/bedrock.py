"""Native Bedrock Converse with explicit bearer credentials and bounded structured output."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from math import isfinite
from typing import Any
from urllib.parse import quote

import httpx

from ase.adapters.llm.bedrock_schema import project_schema
from ase.application.ports.llm import LlmGatewayError, LlmGatewayTimeout
from ase.domain.bedrock import normalise_bedrock_base_url
from ase.domain.llm import MAX_API_KEY_LENGTH, LlmRequest, LlmResult

MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def build_payload(request: LlmRequest) -> dict[str, Any]:
    if request.reasoning_effort is not None:
        raise LlmGatewayError(
            "Bedrock Converse currently supports provider-default reasoning only."
        )
    if (
        type(request.max_output_tokens) is not int
        or not 64 <= request.max_output_tokens <= 32000
        or not isfinite(request.temperature)
        or not 0 <= request.temperature <= 1
    ):
        raise LlmGatewayError("Bedrock received unsupported inference settings.")
    payload: dict[str, Any] = {
        "messages": [
            {
                "role": message.role,
                "content": [{"text": message.content}]
                + [
                    {
                        "image": {
                            "format": "png",
                            "source": {"bytes": base64.b64encode(image.png).decode("ascii")},
                        }
                    }
                    for image in message.images
                ],
            }
            for message in request.messages
            if message.role != "system"
        ],
        "inferenceConfig": {
            "maxTokens": request.max_output_tokens,
            "temperature": request.temperature,
        },
    }
    system = [{"text": message.content} for message in request.messages if message.role == "system"]
    if system:
        payload["system"] = system
    if request.json_schema is not None:
        payload["outputConfig"] = {
            "textFormat": {
                "type": "json_schema",
                "structure": {
                    "jsonSchema": {
                        "name": request.schema_name,
                        "schema": json.dumps(
                            project_schema(request.json_schema), separators=(",", ":")
                        ),
                    }
                },
            }
        }
    return payload


def _reasoning_only(block: dict[str, Any]) -> bool:
    if set(block) != {"reasoningContent"}:
        return False
    value = block["reasoningContent"]
    if not isinstance(value, dict):
        return False
    if set(value) == {"redactedContent"}:
        return isinstance(value["redactedContent"], str)
    if set(value) != {"reasoningText"} or not isinstance(value["reasoningText"], dict):
        return False
    text = value["reasoningText"]
    return (
        set(text) <= {"text", "signature"}
        and isinstance(text.get("text"), str)
        and ("signature" not in text or isinstance(text["signature"], str))
    )


def parse_response(data: Any, model: str, latency_ms: float) -> LlmResult:
    if not isinstance(data, dict):
        raise LlmGatewayError("Bedrock returned an invalid response.")
    stop = data.get("stopReason")
    if stop == "max_tokens":
        raise LlmGatewayError("Bedrock exhausted the completion token budget before finishing.")
    if stop != "end_turn":
        raise LlmGatewayError("Bedrock did not return a completed, unblocked response.")
    output = data.get("output")
    message = output.get("message") if isinstance(output, dict) else None
    blocks = message.get("content") if isinstance(message, dict) else None
    if (
        not isinstance(message, dict)
        or message.get("role") != "assistant"
        or not isinstance(blocks, list)
        or not 1 <= len(blocks) <= 100
    ):
        raise LlmGatewayError("Bedrock returned an invalid assistant message.")
    texts = []
    for block in blocks:
        if isinstance(block, dict) and _reasoning_only(block):
            continue  # Do not persist model reasoning or encrypted reasoning blocks.
        if (
            not isinstance(block, dict)
            or set(block) != {"text"}
            or not isinstance(block["text"], str)
        ):
            raise LlmGatewayError("Bedrock returned unsupported or refused message content.")
        texts.append(block["text"])
    content = "".join(texts)
    if not content.strip():
        raise LlmGatewayError("Bedrock returned an empty message.")
    usage = data.get("usage")
    if not isinstance(usage, dict) or any(
        type(usage.get(key)) is not int or not 0 <= usage[key] <= 1_000_000_000
        for key in ("inputTokens", "outputTokens")
    ):
        raise LlmGatewayError("Bedrock returned invalid token usage.")
    return LlmResult(content, model, latency_ms, usage["inputTokens"], usage["outputTokens"])


def _decode(content: bytearray) -> Any:
    try:
        result = json.loads(content)
    except (ValueError, RecursionError):
        raise LlmGatewayError("Bedrock returned invalid JSON.") from None
    pending = [(result, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > 64:
            raise LlmGatewayError("Bedrock returned excessively nested JSON.")
        if isinstance(value, (dict, list)):
            children = value.values() if isinstance(value, dict) else value
            pending.extend(
                (child, depth + 1) for child in children if isinstance(child, (dict, list))
            )
    return result


class BedrockConverseGateway:
    def __init__(
        self, *, client: httpx.AsyncClient | None = None, timeout_seconds: float = 120
    ) -> None:
        if not isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("Provide a positive finite Bedrock timeout.")
        self._client = client or httpx.AsyncClient(follow_redirects=False)
        self._timeout = min(timeout_seconds, 120)
        self._admission = asyncio.Semaphore(2)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        try:
            base = normalise_bedrock_base_url(base_url)
        except ValueError:
            raise LlmGatewayError(
                "Bedrock requires a canonical regional runtime endpoint."
            ) from None
        if (
            not api_key
            or len(api_key) > MAX_API_KEY_LENGTH
            or not api_key.isascii()
            or any(char.isspace() or not char.isprintable() for char in api_key)
        ):
            raise LlmGatewayError("Bedrock requires a valid API key.")
        if (
            not model
            or len(model) > 2048
            or model in (".", "..")
            or any(char.isspace() or not char.isprintable() for char in model)
        ):
            raise LlmGatewayError("Bedrock requires a valid model or inference profile id.")
        payload = build_payload(request)
        started = time.perf_counter()
        try:
            async with (
                asyncio.timeout(self._timeout),
                self._admission,
                self._client.stream(
                    "POST",
                    f"{base}/model/{quote(model, safe='')}/converse",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Accept-Encoding": "identity",
                        "Content-Type": "application/json",
                    },
                    auth=None,
                    follow_redirects=False,
                    timeout=self._timeout,
                ) as response,
            ):
                if response.status_code != 200:
                    if response.status_code in (400, 415, 422) and any(
                        message.images for message in request.messages
                    ):
                        raise LlmGatewayError(
                            "The configured Bedrock model rejected image analysis or its "
                            "structured output settings. Select a compatible vision model; "
                            "no alternative provider was used."
                        )
                    raise LlmGatewayError(f"Bedrock answered {response.status_code}.")
                if response.headers.get("content-encoding", "identity").strip().lower() not in (
                    "",
                    "identity",
                ):
                    raise LlmGatewayError("Bedrock returned unsupported compressed content.")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise LlmGatewayError("Bedrock exceeded the allowed response size.")
                    content.extend(chunk)
        except (TimeoutError, httpx.TimeoutException):
            raise LlmGatewayTimeout("Bedrock timed out.") from None
        except httpx.HTTPError:
            raise LlmGatewayError("Could not reach Bedrock.") from None
        result = parse_response(_decode(content), model, (time.perf_counter() - started) * 1000)
        if time.perf_counter() - started > self._timeout:
            raise LlmGatewayTimeout("Bedrock timed out.")
        return result
