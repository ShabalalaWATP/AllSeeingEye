"""Per-client limit keys: IPv6 clients share one bucket per /64 prefix."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.client_address import UNKNOWN_CLIENT, rate_limit_key
from ase.domain.errors import InvalidCredentials, RateLimited
from ase.infrastructure.rate_limit import InMemorySlidingWindowLimiter
from helpers import FakeClock


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("192.0.2.10", "192.0.2.10"),
        ("2001:db8:1:2:aaaa:bbbb:cccc:1", "2001:db8:1:2::/64"),
        ("2001:DB8:1:2::ffff", "2001:db8:1:2::/64"),
        ("2001:db8:1:3::1", "2001:db8:1:3::/64"),
        ("::ffff:192.0.2.10", "192.0.2.10"),
        ("::1", "::/64"),
        ("fe80::1%eth0", "fe80::/64"),
        (None, UNKNOWN_CLIENT),
        ("", UNKNOWN_CLIENT),
        ("testclient", "testclient"),
        ("x" * 200, "x" * 64),
    ],
)
def test_rate_limit_key_normalises_addresses(address: str | None, expected: str) -> None:
    assert rate_limit_key(address) == expected


def test_request_context_exposes_the_bucket_but_keeps_the_full_address() -> None:
    context = RequestContext(ip="2001:db8:1:2::99", user_agent="agent")
    assert context.client_key == "2001:db8:1:2::/64"
    assert context.ip == "2001:db8:1:2::99"


def test_limiter_peek_reports_without_recording() -> None:
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    limiter = InMemorySlidingWindowLimiter(clock)
    assert limiter.peek("key", 2, 60) is None
    assert limiter.hit("key", 2, 60) is None
    assert limiter.peek("key", 2, 60) is None
    assert limiter.hit("key", 2, 60) is None
    assert limiter.peek("key", 2, 60) == 60
    assert limiter.peek("key", 2, 60) == 60
    assert limiter.hit("key", 3, 60) is None


async def test_login_limit_spans_an_ipv6_prefix(container: Container) -> None:
    limit = container.limits.login_per_ip
    for index in range(limit):
        # Distinct emails stay under the per-email limit; only the /64 bucket fills.
        context = RequestContext(ip=f"2001:db8:5:6::{index + 1:x}")
        async with container.session_factory() as session:
            with pytest.raises(InvalidCredentials):
                await container.login(session).execute(
                    f"unknown{index}@example.com", "Wrong-Password-1", context
                )
    async with container.session_factory() as session:
        with pytest.raises(RateLimited):
            await container.login(session).execute(
                "another@example.com",
                "Wrong-Password-1",
                RequestContext(ip="2001:db8:5:6:ffff:ffff:ffff:ffff"),
            )
        # A different /64 and an IPv4 client keep their own buckets.
        for ip in ("2001:db8:5:7::1", "192.0.2.44"):
            with pytest.raises(InvalidCredentials):
                await container.login(session).execute(
                    "another@example.com", "Wrong-Password-1", RequestContext(ip=ip)
                )


async def test_ipv4_mapped_clients_share_the_ipv4_bucket(container: Container) -> None:
    limit = container.limits.request_account_per_ip
    for index in range(limit):
        ip = "198.51.100.7" if index % 2 else "::ffff:198.51.100.7"
        async with container.session_factory() as session:
            await container.request_account(session).execute(
                f"mapped{index}@example.com", "Mapped", None, RequestContext(ip=ip)
            )
    async with container.session_factory() as session:
        with pytest.raises(RateLimited):
            await container.request_account(session).execute(
                "mapped-last@example.com", "Mapped", None, RequestContext(ip="198.51.100.7")
            )
