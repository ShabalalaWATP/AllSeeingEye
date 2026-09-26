"""Outbound clients share one verified TLS context and still refuse untrusted certificates."""

from __future__ import annotations

import asyncio
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from ase.adapters.archive.wayback import WaybackArchiver
from ase.adapters.feeds.acled_http import AcledHttpClient
from ase.adapters.feeds.barentswatch_http import BarentsWatchHttpClient
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.llm.bedrock import BedrockConverseGateway
from ase.adapters.llm.embeddings import OpenAiEmbeddingGateway
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.adapters.llm.openai_web_search import OpenAiWebSearchGateway
from ase.adapters.notify import webhook as webhook_module
from ase.adapters.notify.webhook import WebhookNotifier
from ase.adapters.tiles.os_maps import OsMapsTileProvider
from ase.adapters.tls import verified_ssl_context
from ase.domain.warning import alert_from, evaluate
from test_original_http import adapter, request
from test_warning import NOW, indicator
from tracker_helpers import conflict_events


def _context_of(client: httpx.AsyncClient) -> ssl.SSLContext:
    transport = client._transport
    assert isinstance(transport, httpx.AsyncHTTPTransport)
    context = transport._pool._ssl_context
    assert context is not None
    return context


def _self_signed_server(directory: Path) -> ssl.SSLContext:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    certificate_path, key_path = directory / "server.crt", directory / "server.key"
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(str(certificate_path), str(key_path))
    return server


def test_each_shared_context_is_built_once_and_requires_verification() -> None:
    for trust_env in (True, False):
        context = verified_ssl_context(trust_env)
        assert verified_ssl_context(trust_env) is context
        assert context.verify_mode is ssl.CERT_REQUIRED
        assert context.check_hostname is True


async def test_long_lived_application_clients_reuse_the_shared_context() -> None:
    shared, private = verified_ssl_context(), verified_ssl_context(trust_env=False)
    owners: list[tuple[Any, ssl.SSLContext]] = [
        (FeedHttpClient("ase-test"), shared),
        (WaybackArchiver("ase-test"), shared),
        (OpenAiCompatibleGateway(), shared),
        (OpenAiWebSearchGateway(), shared),
        (OpenAiEmbeddingGateway(), shared),
        (BedrockConverseGateway(), shared),
        (OsMapsTileProvider("key"), shared),
        # These fixed-origin credential clients ignore proxy and CA environment settings.
        (AcledHttpClient("ase-test"), private),
        (BarentsWatchHttpClient("ase-test"), private),
    ]
    for owner, expected in owners:
        assert _context_of(owner._client) is expected
        await owner._client.aclose()


async def test_per_request_clients_pass_the_shared_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[object] = []

    class RecordingClient(httpx.AsyncClient):
        def __init__(self, **options: Any) -> None:
            seen.append(options.get("verify"))
            super().__init__(**options)

    async def unpinned(_url: str) -> None:
        return None

    monkeypatch.setattr(httpx, "AsyncClient", RecordingClient)
    monkeypatch.setattr(webhook_module, "assert_public_host", unpinned)
    rule = indicator()
    events = {event.title: event for event in conflict_events(NOW)}
    firing = evaluate(rule, [events["Shelling in Kharkiv"]], NOW, None)
    assert firing is not None
    notifier = WebhookNotifier(
        "https://hooks.example/alert",
        "ase-test",
        transport=httpx.MockTransport(lambda _: httpx.Response(204)),
    )
    assert await notifier.notify(alert_from(rule, firing, uuid4(), NOW), rule) is True
    fetcher = adapter(
        monkeypatch,
        lambda _: httpx.Response(
            200, stream=httpx.ByteStream(b"text"), headers={"content-type": "text/plain"}
        ),
    )
    assert (await fetcher.fetch(request())).body == b"text"
    assert seen == [verified_ssl_context(), verified_ssl_context(trust_env=False)]


async def test_the_shared_context_refuses_an_untrusted_certificate(tmp_path: Path) -> None:
    async def respond(_reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.close()

    server = await asyncio.start_server(respond, "127.0.0.1", 0, ssl=_self_signed_server(tmp_path))
    port = server.sockets[0].getsockname()[1]
    async with server, httpx.AsyncClient(verify=verified_ssl_context()) as client:
        with pytest.raises(httpx.ConnectError, match="CERTIFICATE_VERIFY_FAILED"):
            await asyncio.wait_for(client.get(f"https://127.0.0.1:{port}/"), 5)
