"""A private loopback TLS origin with generated trust and persistent HTTP connections."""

import asyncio
import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


@dataclass
class FeedTlsServer:
    trust: ssl.SSLContext
    port: int = 0
    requests: list[bytes] = field(default_factory=list)
    connections: int = 0
    waiting: asyncio.Event = field(default_factory=asyncio.Event)

    def origin(self, host: str = "source.example") -> str:
        return f"https://{host}:{self.port}"


@asynccontextmanager
async def feed_tls_server(
    directory: Path,
    *,
    names: tuple[str, ...] = ("source.example",),
    cookie: str = "isolation=synthetic; Path=/",
) -> AsyncIterator[FeedTlsServer]:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, names[0])])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(name) for name in names]), False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
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
    server_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_tls.load_cert_chain(certificate_path, key_path)
    result = FeedTlsServer(ssl.create_default_context(cafile=str(certificate_path)))
    writers: set[asyncio.StreamWriter] = set()
    tasks: set[asyncio.Task[None]] = set()

    async def respond(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writers.add(writer)
        result.connections += 1
        try:
            while True:
                request = await reader.readuntil(b"\r\n\r\n")
                result.requests.append(request)
                if request.startswith(b"GET /wait "):
                    result.waiting.set()
                    await reader.read()
                    break
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nSet-Cookie: "
                    + cookie.encode("ascii")
                    + b"\r\n\r\nok"
                )
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            writers.discard(writer)

    def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.create_task(respond(reader, writer))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    server = await asyncio.start_server(connected, "127.0.0.1", 0, ssl=server_tls)
    result.port = server.sockets[0].getsockname()[1]
    try:
        yield result
    finally:
        server.close()
        await server.wait_closed()
        for writer in tuple(writers):
            writer.close()
        if tasks:
            await asyncio.gather(*tasks)
