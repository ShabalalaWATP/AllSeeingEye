"""Shared connector plumbing: unchanged upstreams, JSON list members and the constructor."""

from __future__ import annotations

import pytest

from ase.adapters.feeds.base import HttpFeed, empty_when_unchanged, json_list
from ase.adapters.feeds.http import FeedFetchError, NotModified
from ase.domain.events import Event
from feeds_helpers import NOW, FakeClock, FakeHttp


class _Probe(HttpFeed):
    def __init__(self, http: FakeHttp, error: Exception | None = None) -> None:
        super().__init__(http, FakeClock(NOW))  # type: ignore[arg-type]
        self.error = error
        self.calls = 0

    @empty_when_unchanged
    async def fetch(self) -> list[Event]:
        """Probe docstring."""
        self.calls += 1
        await self._http.get_json("https://example.org/feed.json")
        if self.error is not None:
            raise self.error
        return []


async def test_unchanged_upstream_is_an_empty_batch() -> None:
    probe = _Probe(FakeHttp(not_modified=True))

    assert await probe.fetch() == []
    assert probe.calls == 1


async def test_other_failures_still_reach_the_scheduler() -> None:
    probe = _Probe(FakeHttp({"feed.json": {}}), FeedFetchError("upstream refused"))

    with pytest.raises(FeedFetchError, match="upstream refused"):
        await probe.fetch()


def test_the_wrapped_fetch_keeps_its_identity() -> None:
    assert _Probe.fetch.__name__ == "fetch"
    assert _Probe.fetch.__doc__ == "Probe docstring."


def test_constructor_holds_the_shared_client_and_clock() -> None:
    http = FakeHttp()
    probe = _Probe(http)

    assert probe._http is http
    assert probe._clock.now() == NOW


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"features": [{"id": "a"}]}, [{"id": "a"}]),
        ({"type": "FeatureCollection"}, []),
        ([{"id": "a"}], []),
        (None, []),
        ("features", []),
        # The member is returned as sent, so each connector keeps its own item checks.
        ({"features": {"id": "a"}}, {"id": "a"}),
    ],
)
def test_json_list_reads_one_member_of_a_json_object(payload: object, expected: object) -> None:
    assert json_list(payload, "features") == expected


def test_not_modified_is_not_a_fetch_error() -> None:
    """A 304 must never be swallowed by a connector's own FeedFetchError handling."""
    assert not issubclass(NotModified, FeedFetchError)
