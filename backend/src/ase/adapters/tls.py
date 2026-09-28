"""One verified TLS context per process, shared by every outbound httpx client.

httpx builds a new SSL context for each client and parses the whole CA bundle every
time, which costs about a quarter of a second on Windows. The composition root builds a
dozen clients, so identical copies used to dominate start-up. This module builds each
variant once with httpx's own factory, so verification is unchanged: the certifi bundle,
or SSL_CERT_FILE and SSL_CERT_DIR when the client trusts the environment, with hostname
checks and certificate verification always required. Nothing here can disable either.

Sharing is safe because an SSLContext holds configuration rather than connection state.
httpcore writes the ALPN list to the context before each handshake; every client here
speaks HTTP/1.1 only, so that write is always the same value.
"""

from __future__ import annotations

import ssl
from functools import cache

import httpx


@cache
def verified_ssl_context(trust_env: bool = True) -> ssl.SSLContext:
    """The shared verified context; pass the client's own ``trust_env`` setting."""
    return httpx.create_ssl_context(verify=True, trust_env=trust_env)
