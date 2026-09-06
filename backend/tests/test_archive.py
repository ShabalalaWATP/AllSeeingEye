"""Wayback archiving: the adapter against a mocked archive.org, and the job after generation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
from httpx import AsyncClient

from ase.adapters.archive.wayback import NullArchiver, WaybackArchiver
from ase.application.ports.feeds import EventQuery
from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, filled_store, good_body

PUBLISHED = datetime(2026, 9, 4, 22, 0, tzinfo=UTC)
SNAPSHOT = "https://web.archive.org/web/20260905010000/https://example.com/a"


def snapshot(timestamp: str) -> dict[str, Any]:
    return {
        "closest": {
            "available": True,
            "url": f"http://web.archive.org/web/{timestamp}/https://example.com/a",
            "timestamp": timestamp,
            "status": "200",
        }
    }


class FakeArchive:
    """archive.org and web.archive.org as one transport, recording what was asked."""

    def __init__(
        self,
        available: dict[str, Any] | None = None,
        *,
        save_status: int = 200,
        save_location: str | None = "/web/20260905010000/https://example.com/a",
        broken: bool = False,
    ) -> None:
        self.available = available
        self.save_status = save_status
        self.save_location = save_location
        self.broken = broken
        self.calls: list[str] = []
        self.sleeps: list[float] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(f"{request.method} {request.url.host}{request.url.path}")
        if self.broken:
            raise httpx.ConnectError("down", request=request)
        if request.url.host == "archive.org":
            return httpx.Response(200, json={"archived_snapshots": self.available or {}})
        headers = {"Content-Location": self.save_location} if self.save_location else {}
        return httpx.Response(self.save_status, headers=headers, text="<html></html>")

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)

    def archiver(self) -> WaybackArchiver:
        client = httpx.AsyncClient(transport=httpx.MockTransport(self.handle))
        return WaybackArchiver("ase-tests", client=client, sleeper=self.sleep)


async def test_reuses_a_snapshot_taken_since_publication() -> None:
    fake = FakeArchive(snapshot("20260905000000"))
    archiver = fake.archiver()
    assert (
        await archiver.archive("https://example.com/a", PUBLISHED)
        == "https://web.archive.org/web/20260905000000/https://example.com/a"
    )
    assert fake.calls == ["GET archive.org/wayback/available"] and fake.sleeps == []
    await archiver.aclose()


async def test_saves_when_the_only_snapshot_predates_publication() -> None:
    fake = FakeArchive(snapshot("20260901000000"))
    archiver = fake.archiver()
    assert await archiver.archive("https://example.com/a", PUBLISHED) == SNAPSHOT
    assert fake.calls[-1] == "GET web.archive.org/save/https://example.com/a"
    assert fake.sleeps == [4.0]
    await archiver.aclose()


async def test_failures_and_bad_input_yield_no_archive() -> None:
    refused = FakeArchive(save_status=429)
    assert await refused.archiver().archive("https://example.com/a", PUBLISHED) is None
    silent = FakeArchive(save_location=None)
    assert await silent.archiver().archive("https://example.com/a", PUBLISHED) is None
    down = FakeArchive(broken=True)
    assert await down.archiver().archive("https://example.com/a", PUBLISHED) is None
    odd = FakeArchive(
        {"closest": {"available": True, "url": "https://evil.example/x"}}, save_location=None
    )
    assert await odd.archiver().archive("https://example.com/a", PUBLISHED) is None
    stamped = FakeArchive(
        {"closest": {"available": True, "url": SNAPSHOT, "timestamp": "soon"}}, save_status=500
    )
    assert await stamped.archiver().archive("https://example.com/a", PUBLISHED) is None
    untouched = FakeArchive()
    archiver = untouched.archiver()
    assert await archiver.archive("ftp://example.com/a", PUBLISHED) is None
    assert await archiver.archive("javascript:alert(1)", PUBLISHED) is None
    assert await archiver.archive("https://" + "a" * 2_000, PUBLISHED) is None
    assert untouched.calls == []
    assert await NullArchiver().archive("https://example.com/a", PUBLISHED) is None


class RecordingArchiver:
    def __init__(self) -> None:
        self.urls: list[str] = []

    async def archive(self, url: str, published_at: datetime) -> str | None:
        self.urls.append(url)
        if url.endswith("/a"):
            return None
        return f"https://web.archive.org/web/20260905000000/{url}"

    async def aclose(self) -> None:
        return None


async def test_cited_evidence_is_archived_after_generation(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, PROFILE)
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    archiver = RecordingArchiver()
    container.archiver = archiver
    judgements = good_body()["key_judgements"]
    fits = good_body(
        key_judgements=[judgements[0], {**judgements[1], "supporting_evidence": ["E2"]}]
    )
    container.llm = ScriptedGateway(json.dumps(fits))
    created = await client.post(
        "/api/reports", json={"template": "intrep", "country": "ua"}, headers=bearer(token)
    )
    assert created.status_code == 201
    assert all(item["archive_url"] is None for item in created.json()["version"]["evidence"])
    # The background task has run by the time the response is delivered through the transport.
    assert archiver.urls == ["https://example.com/e", "https://example.com/a"]

    fetched = await client.get(
        f"/api/reports/{created.json()['report']['id']}", headers=bearer(token)
    )
    evidence = fetched.json()["version"]["evidence"]
    assert (
        evidence[0]["archive_url"]
        == "https://web.archive.org/web/20260905000000/https://example.com/e"
    )
    assert evidence[1]["archive_url"] is None
    assert (
        "[archive](https://web.archive.org/web/20260905000000/https://example.com/e)"
        in (fetched.json()["version"]["markdown"])
    )
