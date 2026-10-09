"""Preserve the logical origin in HTTPcore while connecting only to checked IPs.

HTTPX has no public hook for its network backend. Installation below is deliberately
limited to the locked direct AsyncHTTPTransport/AsyncConnectionPool combination;
it retains its TLS context, limits and lifecycle. Proxies and unknown transports
fail closed. Real TLS regressions must accompany HTTPX/HTTPcore upgrades.
"""

import ipaddress
from collections.abc import Iterable
from contextvars import ContextVar
from http.cookiejar import Cookie, CookieJar

import httpcore
import httpx

ORIGINAL_HOST = "ase_original_host"
_destination: ContextVar[tuple[str, int, str] | None] = ContextVar(
    "feed_checked_destination", default=None
)


class _NoCookies(CookieJar):
    def set_cookie(self, cookie: Cookie) -> None:
        """Feed credentials are explicit per-request headers, never response cookies."""


class _PinnedBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, backend: httpcore.AsyncNetworkBackend) -> None:
        self._backend = backend

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        checked = _destination.get()
        if checked is None or checked[:2] != (host, port):
            raise httpcore.ConnectError("Feed connection has no checked destination")
        return await self._backend.connect_tcp(
            checked[2], port, timeout, local_address, socket_options
        )

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


class OriginPinnedTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport) -> None:
        self.inner = transport
        self._direct = False
        if type(transport) is httpx.AsyncHTTPTransport:
            pool = transport._pool
            if (
                type(pool) is httpcore.AsyncConnectionPool
                and pool._proxy is None
                and pool._uds is None
                and not pool.connections
            ):
                pool._network_backend = _PinnedBackend(pool._network_backend)
                self._direct = True

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if not self._direct:
            raise httpx.ConnectError("Feed transport requires a fresh direct HTTP connection pool")
        address = request.url.host
        try:
            ipaddress.ip_address(address)
        except ValueError:
            raise httpx.ConnectError("Feed transport requires a checked IP address") from None
        host = request.extensions.get(ORIGINAL_HOST, address)
        if not isinstance(host, str):
            raise httpx.ConnectError("Feed transport requires an original hostname")
        url = request.url.copy_with(host=host)
        port = url.port or (443 if url.scheme == "https" else 80)
        # The original authority now owns pooling and TLS identity. Only the TCP
        # connect operation sees the checked IP. Existing same-origin connections
        # remain pinned to the public address checked when they were established.
        outgoing = httpx.Request(
            request.method,
            url,
            headers=request.headers,
            stream=request.stream,
            extensions=request.extensions,
        )
        token = _destination.set((url.raw_host.decode("ascii"), port, address))
        try:
            return await self.inner.handle_async_request(outgoing)
        finally:
            _destination.reset(token)

    async def aclose(self) -> None:
        await self.inner.aclose()


def isolate_feed_client(client: httpx.AsyncClient) -> None:
    """Own all dispatch paths, including subclass calls and injected client mounts."""
    if client.cookies or "cookie" in client.headers:
        raise ValueError("Shared feed clients must not carry cookies.")
    client.cookies = _NoCookies()
    wrapped: dict[httpx.AsyncBaseTransport, httpx.AsyncBaseTransport] = {}

    def wrap(transport: httpx.AsyncBaseTransport) -> httpx.AsyncBaseTransport:
        if isinstance(transport, OriginPinnedTransport):
            return transport
        if isinstance(transport, httpx.MockTransport):
            return transport  # Offline fixtures perform no network connection or pooling.
        if transport not in wrapped:
            wrapped[transport] = OriginPinnedTransport(transport)
        return wrapped[transport]

    client._transport = wrap(client._transport)
    client._mounts = {
        pattern: wrap(transport) if transport is not None else None
        for pattern, transport in client._mounts.items()
    }
