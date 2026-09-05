"""Per-user cap on live streams."""

from __future__ import annotations

from uuid import uuid4

from ase.application.feeds.streams import StreamLimiter


def test_limiter_counts_per_user() -> None:
    limiter = StreamLimiter(max_per_user=2)
    alice, bob = uuid4(), uuid4()
    assert limiter.acquire(alice) and limiter.acquire(alice)
    assert not limiter.acquire(alice)
    assert limiter.acquire(bob)
    assert limiter.held(alice) == 2 and limiter.held(bob) == 1
    limiter.release(alice)
    assert limiter.acquire(alice)
    limiter.release(alice)
    limiter.release(alice)
    limiter.release(alice)  # releasing below zero is harmless
    assert limiter.held(alice) == 0
