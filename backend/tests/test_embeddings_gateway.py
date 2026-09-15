"""Embeddings provider boundary rejects malformed, excessive or non-finite replies."""

import asyncio
import gzip
import json
from typing import Any

import httpx
import pytest

from ase.adapters.llm.embeddings import MAX_RESPONSE_BYTES, OpenAiEmbeddingGateway, parse_embeddings
from ase.application.ports.embeddings import EmbeddingGatewayError
from ase.domain.report_search import checked_vector, cosine


def payload(*vectors: object) -> dict[str, Any]:
    return {"data": [{"index": i, "embedding": vector} for i, vector in enumerate(vectors)]}


@pytest.mark.parametrize(
    "data",
    [
        [],
        {},
        {"data": []},
        {"data": [None]},
        {"data": [{"index": False, "embedding": [1]}]},
        {"data": [{"index": 1, "embedding": [1]}]},
        payload([True]),
        payload(["1"]),
        payload([float("nan")]),
        payload([float("inf")]),
        payload([0, 0]),
        payload([]),
        payload(None),
        payload([1] * 4097),
        payload([10**400]),
    ],
)
def test_bad_embedding_replies(data: object) -> None:
    with pytest.raises(EmbeddingGatewayError):
        parse_embeddings(data, 1, 0)


def test_order_dimension_duplicates_and_usage() -> None:
    parsed = parse_embeddings(
        {
            "data": [{"index": 1, "embedding": [0, 2]}, {"index": 0, "embedding": [3, 0]}],
            "usage": {"prompt_tokens": 7},
        },
        2,
        5,
    )
    assert parsed.vectors == ((1, 0), (0, 1)) and parsed.prompt_tokens == 7
    assert cosine(parsed.vectors[0], parsed.vectors[1]) == 0
    with pytest.raises(ValueError, match="dimensions differ"):
        cosine((1.0,), (1.0, 0.0))
    with pytest.raises(EmbeddingGatewayError):
        parse_embeddings(payload([1], [1, 0]), 2, 0)
    with pytest.raises(EmbeddingGatewayError):
        parse_embeddings({"data": [{"index": 0, "embedding": [1]}] * 2}, 2, 0)
    assert checked_vector((3.0, 4.0)) == (0.6, 0.8)
    assert (
        parse_embeddings({**payload([1]), "usage": {"prompt_tokens": True}}, 1, 0).prompt_tokens
        is None
    )


async def test_request_shape_and_safe_errors() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=payload([1, 2]))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gateway = OpenAiEmbeddingGateway(client=client)
    result = await gateway.embed(
        "http://localhost:11434/v1", "test-secret", "local-model", ["text"]
    )
    assert len(result.vectors) == 1
    assert str(calls[0].url) == "http://localhost:11434/v1/embeddings"
    assert calls[0].headers["authorization"] == "Bearer test-secret"
    assert calls[0].headers["accept-encoding"] == "identity"
    assert json.loads(calls[0].content) == {
        "model": "local-model",
        "input": ["text"],
        "encoding_format": "float",
    }
    await gateway.embed("http://localhost/v1", "", "local", ["text"])
    assert "authorization" not in calls[1].headers
    for texts in ([], [""], ["a" * 6001], ["a"] * 9):
        with pytest.raises(EmbeddingGatewayError):
            await gateway.embed("http://localhost/v1", "", "local", texts)
    await gateway.aclose()


# A genuine loopback endpoint, so failures come from the response under test rather than the
# HTTPS rule for remote model hosts.
LOCAL = "http://localhost:11434/v1"


@pytest.mark.parametrize(
    "status,body", [(401, b"test-secret"), (302, b""), (200, b"invalid"), (200, b"[" * 2000)]
)
async def test_status_json_and_redirect_failure(status: int, body: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body, headers={"location": "http://other.test"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EmbeddingGatewayError) as caught:
            await OpenAiEmbeddingGateway(client=client).embed(LOCAL, "test-secret", "m", ["t"])
        assert "test-secret" not in str(caught.value)


async def test_response_cap_transport_error_and_total_deadline() -> None:
    class LargeStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b" " * MAX_RESPONSE_BYTES
            yield b" "

    def oversized(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=LargeStream())

    def transport_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("test-secret")

    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json=payload([1]))

    for handler in (oversized, transport_error, slow):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(EmbeddingGatewayError) as caught:
                await OpenAiEmbeddingGateway(client=client, timeout_seconds=0.01).embed(
                    LOCAL, "test-secret", "m", ["t"]
                )
            assert "test-secret" not in str(caught.value)
    gateway = OpenAiEmbeddingGateway()
    await gateway.aclose()


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "br", "identity, gzip", "unknown"])
async def test_compressed_response_is_rejected_before_body_read(encoding: str) -> None:
    # A small controlled compressed payload demonstrates the allocation boundary.
    compressed = gzip.compress(b"provider echoed test-secret " * 2048)
    consumed = False

    class CompressedStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            nonlocal consumed
            consumed = True
            yield compressed

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"Content-Encoding": encoding}, stream=CompressedStream()
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EmbeddingGatewayError) as caught:
            await OpenAiEmbeddingGateway(client=client).embed(
                LOCAL, "test-secret", "m", ["private report text"]
            )
    assert not consumed
    assert "test-secret" not in str(caught.value)
    assert "private report text" not in str(caught.value)


async def test_explicit_identity_encoding_is_accepted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Encoding": "identity"}, json=payload([1]))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAiEmbeddingGateway(client=client).embed(LOCAL, "", "m", ["t"])
    assert result.vectors == ((1.0,),)
