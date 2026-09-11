"""Native Responses compatibility for explicitly requested OpenAI max reasoning."""

import base64
from typing import Any

from ase.adapters.llm.model_discovery import model_id
from ase.application.ports.llm import LlmGatewayError
from ase.domain.llm import LlmMessage, LlmRequest, LlmResult

OPENAI_BASE = "https://api.openai.com/v1"
RESPONSES_URL = OPENAI_BASE + "/responses"


def uses_responses(base_url: str, request: LlmRequest) -> bool:
    """Never infer native API capability for an administrator's compatible endpoint."""
    return base_url.rstrip("/") == OPENAI_BASE and request.reasoning_effort == "max"


def _content(message: LlmMessage) -> str | list[dict[str, Any]]:
    if not message.images:
        return message.content
    return [{"type": "input_text", "text": message.content}] + [
        {
            "type": "input_image",
            "image_url": "data:image/png;base64," + base64.b64encode(image.png).decode("ascii"),
            "detail": "high",
        }
        for image in message.images
    ]


def build_responses_payload(model: str, request: LlmRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": [
            {"role": message.role, "content": _content(message)} for message in request.messages
        ],
        "reasoning": {"effort": request.reasoning_effort},
        "max_output_tokens": request.max_output_tokens,
        "store": False,
    }
    if request.json_schema is not None:
        payload["text"] = {
            "format": {
                "type": "json_schema",
                "name": request.schema_name,
                "strict": True,
                "schema": dict(request.json_schema),
            }
        }
    return payload


def _message_text(item: dict[str, Any]) -> str:
    if item.get("status") != "completed" or item.get("role") != "assistant":
        raise LlmGatewayError("The model endpoint returned an unfinished or invalid message.")
    parts = item.get("content")
    if not isinstance(parts, list) or not parts:
        raise LlmGatewayError("The model endpoint returned an invalid message body.")
    text: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "refusal":
            raise LlmGatewayError("The selected model declined the request.")
        if (
            not isinstance(part, dict)
            or part.get("type") != "output_text"
            or not isinstance(part.get("text"), str)
        ):
            raise LlmGatewayError("The model endpoint returned invalid text output.")
        text.append(part["text"])
    return "".join(text)


def _usage(data: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = data.get("usage")
    if usage is None:
        return None, None
    if not isinstance(usage, dict):
        raise LlmGatewayError("The model endpoint returned invalid usage data.")
    tokens: list[int | None] = []
    for key in ("input_tokens", "output_tokens"):
        value = usage.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise LlmGatewayError("The model endpoint returned invalid usage data.")
        tokens.append(value)
    return tokens[0], tokens[1]


def parse_response(data: Any, fallback_model: str, latency_ms: float) -> LlmResult:
    if not isinstance(data, dict):
        raise LlmGatewayError("The model endpoint returned something other than an object.")
    if data.get("status") == "incomplete":
        raise LlmGatewayError(
            "The model response was incomplete. It may have exhausted its completion token "
            "budget; check the configured budget and reasoning effort."
        )
    if data.get("status") != "completed" or data.get("error") is not None:
        raise LlmGatewayError("The model endpoint did not return a completed response.")
    output = data.get("output")
    if not isinstance(output, list) or not output:
        raise LlmGatewayError("The model endpoint returned no output messages.")
    messages: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            raise LlmGatewayError("The model endpoint returned an invalid output item.")
        if item.get("type") == "reasoning":
            # Reasoning summaries are not the requested assistant answer.
            continue
        if item.get("type") != "message":
            raise LlmGatewayError("The model endpoint returned an unexpected output type.")
        messages.append(_message_text(item))
    content = "\n\n".join(messages)
    if not content.strip():
        raise LlmGatewayError("The model returned an empty message.")
    prompt, completion = _usage(data)
    return LlmResult(
        content=content,
        model=model_id(data.get("model") or fallback_model),
        latency_ms=latency_ms,
        prompt_tokens=prompt,
        completion_tokens=completion,
    )
