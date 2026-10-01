"""Single-flight sharing of identical public reads, with bounded short-lived results."""

from __future__ import annotations

import asyncio

import pytest

from ase.application.feeds.shared_reads import SharedReads
from ase.domain.errors import RateLimited


class Loader:
    def __init__(self) -> None:
        self.calls = 0
        self.release = asyncio.Event()

    async def __call__(self) -> list[int]:
        self.calls += 1
        await self.release.wait()
        return [self.calls]


async def test_ten_identical_reads_share_one_load() -> None:
    reads: SharedReads[list[int]] = SharedReads()
    load = Loader()
    tasks = [asyncio.create_task(reads.read(("q", 1), load, actor=f"user:{i}")) for i in range(10)]
    await asyncio.sleep(0)
    load.release.set()
    results = await asyncio.gather(*tasks)
    assert load.calls == 1 and reads.loads == 1 and reads.shared == 9
    assert all(result is results[0] for result in results)


async def test_other_queries_and_generations_load_separately() -> None:
    reads: SharedReads[list[int]] = SharedReads()
    load = Loader()
    load.release.set()
    await reads.read(("q", 1), load, actor="a")
    await reads.read(("q", 2), load, actor="a")
    await reads.read(("other", 1), load, actor="a")
    assert load.calls == 3
    # A recent identical read is reused until it expires or is displaced.
    assert await reads.read(("q", 1), load, actor="b") == [1]
    assert load.calls == 3


async def test_results_are_bounded_by_count_and_lifetime() -> None:
    now = [0.0]
    reads: SharedReads[list[int]] = SharedReads(
        max_results=2, ttl_seconds=2, monotonic=lambda: now[0]
    )
    load = Loader()
    load.release.set()
    for key in ("a", "b", "c"):
        await reads.read(key, load, actor="x")
    assert len(reads) == 2
    await reads.read("a", load, actor="x")  # Displaced, so loaded again.
    assert load.calls == 4
    now[0] = 2.5
    await reads.read("c", load, actor="x")
    assert load.calls == 5 and len(reads) == 1


async def test_a_result_that_changed_during_its_load_is_shared_but_not_kept() -> None:
    reads: SharedReads[list[int]] = SharedReads()
    load = Loader()
    load.release.set()
    await reads.read("q", load, actor="a", current=lambda: False)
    await reads.read("q", load, actor="a")
    assert load.calls == 2


async def test_a_failed_or_cancelled_leader_never_hands_its_failure_to_others() -> None:
    reads: SharedReads[str] = SharedReads()
    gate = asyncio.Event()
    calls: list[str] = []

    def loader(name: str, fail: bool):
        async def load() -> str:
            calls.append(name)
            await gate.wait()
            if fail:
                raise RateLimited(1)
            return name

        return load

    leader = asyncio.create_task(reads.read("q", loader("leader", True), actor="a"))
    await asyncio.sleep(0)
    joiners = [
        asyncio.create_task(reads.read("q", loader(f"joiner{i}", False), actor=f"b{i}"))
        for i in range(2)
    ]
    await asyncio.sleep(0)
    gate.set()
    with pytest.raises(RateLimited):
        await leader
    assert sorted(await asyncio.gather(*joiners)) == ["joiner0", "joiner1"]

    gate.clear()
    first = asyncio.create_task(reads.read("r", loader("first", False), actor="a"))
    await asyncio.sleep(0)
    waiting = asyncio.create_task(reads.read("r", loader("unused", False), actor="b"))
    await asyncio.sleep(0)
    waiting.cancel()
    gate.set()
    # A waiting caller's cancellation leaves the shared read running for the leader.
    assert await first == "first"
    with pytest.raises(asyncio.CancelledError):
        await waiting
    assert "unused" not in calls


async def test_one_actor_keeps_its_existing_concurrency_bound() -> None:
    reads: SharedReads[list[int]] = SharedReads(max_per_actor=2)
    load = Loader()
    held = [asyncio.create_task(reads.read("q", load, actor="user:a")) for _ in range(2)]
    await asyncio.sleep(0)
    with pytest.raises(RateLimited):
        await reads.read("q", load, actor="user:a")
    other = asyncio.create_task(reads.read("q", load, actor="user:b"))
    load.release.set()
    await asyncio.gather(*held, other)
    # Released afterwards, so the actor can read again.
    assert await reads.read("q", load, actor="user:a") == [1]


def test_bounds_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="negative"):
        SharedReads(max_results=-1)
