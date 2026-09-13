"""Exercise HTTPS pinning with a real local TLS handshake and certificate checks."""

from __future__ import annotations

import asyncio
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ase.adapters.notify import webhook as webhook_module
from ase.adapters.notify.webhook import WebhookNotifier
from ase.domain.warning import alert_from, evaluate
from test_warning import NOW, indicator
from tracker_helpers import conflict_events


def _tls_contexts(directory: Path) -> tuple[ssl.SSLContext, ssl.SSLContext]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "webhook.test")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("webhook.test")]), False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
        .sign(key, hashes.SHA256())
    )
    certificate_path = directory / "webhook.crt"
    key_path = directory / "webhook.key"
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server.load_cert_chain(str(certificate_path), str(key_path))
    client = ssl.create_default_context(cafile=str(certificate_path))
    return server, client


async def test_pinned_https_webhook_verifies_original_hostname(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server_tls, client_tls = _tls_contexts(tmp_path)
    seen: list[bytes] = []

    async def respond(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            headers = await reader.readuntil(b"\r\n\r\n")
            seen.append(headers)
            length = next(
                (
                    int(line.split(b":", 1)[1].strip())
                    for line in headers.split(b"\r\n")
                    if line.lower().startswith(b"content-length:")
                ),
                0,
            )
            if length:
                await reader.readexactly(length)
            response_head = b"HTTP/1.1 204 No Content\r\n"
            response_headers = b"Content-Length: 0\r\nConnection: close\r\n\r\n"
            writer.write(response_head + response_headers)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(respond, "127.0.0.1", 0, ssl=server_tls)
    port = server.sockets[0].getsockname()[1] if server.sockets else 0

    async def checked_address(url: str) -> str:
        return "127.0.0.1"

    monkeypatch.setattr(webhook_module, "assert_public_host", checked_address)
    rule = indicator()
    events = {event.title: event for event in conflict_events(NOW)}
    firing = evaluate(rule, [events["Shelling in Kharkiv"]], NOW, None)
    assert firing is not None
    alert = alert_from(rule, firing, uuid4(), NOW)
    async with server:
        valid = WebhookNotifier(
            f"https://webhook.test:{port}/hook",
            "ase-test",
            transport=httpx.AsyncHTTPTransport(verify=client_tls),
        )
        invalid = WebhookNotifier(
            f"https://wrong.test:{port}/hook",
            "ase-test",
            transport=httpx.AsyncHTTPTransport(verify=client_tls),
        )
        assert await asyncio.wait_for(valid.notify(alert, rule), 3) is True
        assert await asyncio.wait_for(invalid.notify(alert, rule), 3) is False
    assert len(seen) == 1
    assert f"Host: webhook.test:{port}".encode() in seen[0]
