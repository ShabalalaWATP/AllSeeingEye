"""OpenAI-compatible embeddings using the administrator's model endpoint trust boundary."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Sequence
from typing import Any

import httpx

from ase.application.ports.embeddings import EmbeddingGatewayError
from ase.domain.report_search import INDEX_BATCH, MAX_TEXT_CHARS, EmbeddingResult, checked_vector

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 30.0
SAFE_ERROR = "The embeddings endpoint could not produce valid vectors. Check Admin, Models."


def parse_embeddings(data: Any, count: int, latency_ms: float) -> EmbeddingResult:
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        raise EmbeddingGatewayError(SAFE_ERROR)
    rows = data["data"]
    if len(rows) != count:
        raise EmbeddingGatewayError(SAFE_ERROR)
    vectors: dict[int, tuple[float, ...]] = {}
    try:
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid row.")
            index = row.get("index")
            if type(index) is not int or index not in range(count) or index in vectors:
                raise ValueError("Invalid index.")
            vectors[index] = checked_vector(row.get("embedding"))
        if len({len(vector) for vector in vectors.values()}) != 1:
            raise ValueError("Inconsistent dimensions.")
    except (ValueError, OverflowError) as exc:
        raise EmbeddingGatewayError(SAFE_ERROR) from exc
    usage = data.get("usage")
    tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    return EmbeddingResult(
        vectors=tuple(vectors[index] for index in range(count)),
        latency_ms=latency_ms,
        prompt_tokens=tokens if type(tokens) is int and 0 <= tokens <= 10_000_000 else None,
    )


class OpenAiEmbeddingGateway:
    def __init__(
        self, *, client: httpx.AsyncClient | None = None, timeout_seconds: float = TIMEOUT_SECONDS
    ) -> None:
        self._client = client or httpx.AsyncClient(follow_redirects=False)
        self._timeout = timeout_seconds

    async def aclose(self) -> None:
        await self._client.aclose()

    async def embed(
        self, base_url: str, api_key: str, model: str, texts: Sequence[str]
    ) -> EmbeddingResult:
        if not 1 <= len(texts) <= INDEX_BATCH or any(
            not text.strip() or len(text) > MAX_TEXT_CHARS for text in texts
        ):
            raise EmbeddingGatewayError(SAFE_ERROR)
        headers = {"Content-Type": "application/json", "Accept-Encoding": "identity"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._timeout):
                async with self._client.stream(
                    "POST",
                    f"{base_url}/embeddings",
                    headers=headers,
                    json={"model": model, "input": list(texts), "encoding_format": "float"},
                    timeout=self._timeout,
                    follow_redirects=False,
                ) as response:
                    if response.status_code != 200:
                        raise EmbeddingGatewayError(SAFE_ERROR)
                    # HTTPX decompresses before yielding bytes. Refuse compression before
                    # consuming the stream so the response cap also bounds allocations.
                    if (
                        response.headers.get("content-encoding", "identity").strip().lower()
                        != "identity"
                    ):
                        raise EmbeddingGatewayError(SAFE_ERROR)
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise EmbeddingGatewayError(SAFE_ERROR)
                        content.extend(chunk)
            data = json.loads(content)
        except (httpx.HTTPError, TimeoutError, ValueError, RecursionError) as exc:
            raise EmbeddingGatewayError(SAFE_ERROR) from exc
        return parse_embeddings(data, len(texts), (time.perf_counter() - started) * 1000)
