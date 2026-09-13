"""Bounded OpenAI-compatible model discovery using only explicitly supplied credentials."""

import json
from typing import Any

import httpx

from ase.application.ports.llm import LlmGatewayError
from ase.domain.llm import normalise_base_url

MAX_DISCOVERY_BYTES = 512 * 1024
MAX_MODELS = 1000


def model_id(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 120
        or any(char.isspace() or not char.isprintable() for char in value)
    ):
        raise LlmGatewayError("The model endpoint returned an invalid model id.")
    return value


def parse_models(data: Any) -> tuple[str, ...]:
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list) or len(rows) > MAX_MODELS:
        raise LlmGatewayError("The model discovery endpoint returned an invalid model list.")
    names = set()
    for row in rows:
        name = row.get("id") if isinstance(row, dict) else None
        names.add(model_id(name))
    return tuple(sorted(names))


async def discover_models(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
) -> tuple[str, ...]:
    try:
        base_url = normalise_base_url(base_url)
    except ValueError:
        raise LlmGatewayError("The model endpoint address is invalid.") from None
    # An explicit empty header prevents inherited client Authorization from being sent
    # when an administrator intentionally supplies an unauthenticated local endpoint.
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Authorization": f"Bearer {api_key}" if api_key else "",
    }
    async with client.stream(
        "GET",
        f"{base_url}/models",
        headers=headers,
        auth=None,
        timeout=15,
        follow_redirects=False,
    ) as response:
        if response.status_code != 200:
            raise LlmGatewayError(f"The model discovery endpoint answered {response.status_code}.")
        if response.headers.get("content-encoding", "identity").strip().lower() not in (
            "",
            "identity",
        ):
            raise LlmGatewayError("The model discovery endpoint returned compressed content.")
        content = bytearray()
        async for chunk in response.aiter_bytes():
            if len(content) + len(chunk) > MAX_DISCOVERY_BYTES:
                raise LlmGatewayError(
                    "The model discovery endpoint exceeded its response size limit."
                )
            content.extend(chunk)
    try:
        data = json.loads(content)
    except (ValueError, RecursionError):
        raise LlmGatewayError("The model discovery endpoint returned invalid JSON.") from None
    pending = [(data, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > 64:
            raise LlmGatewayError("The model discovery endpoint returned invalid JSON.")
        children = value.values() if isinstance(value, dict) else value
        if isinstance(value, (dict, list)):
            pending.extend(
                (child, depth + 1) for child in children if isinstance(child, (dict, list))
            )
    return parse_models(data)
