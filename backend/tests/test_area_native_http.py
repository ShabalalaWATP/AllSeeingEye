"""Saved-area HTTP creation exercises native composition through mocked transport."""

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.adapters.research_records.copernicus_research import SOURCE_ID
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, good_body
from test_copernicus_research_geometry import payload
from test_map_research_origin import setup
from test_map_research_preview import headers
from test_saved_map_views import revise

START = datetime(2020, 1, 1, 10, 0, 0, 123456, tzinfo=UTC)
END = START + timedelta(minutes=20, microseconds=1)


@pytest.mark.parametrize("disable_at", ["never", "before", "during", "outside"])
async def test_native_area_http_preserves_interval_and_source_admission(
    client, container, user, admin, monkeypatch, disable_at
):
    parent, claims, view, revision, _ = await setup(client, container, user)
    await revise(container, claims, view, revision)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    gateway = ScriptedGateway("{}", json.dumps(good_body()))
    container.llm = gateway
    calls, guarded = [], []

    async def disable():
        async with container.source_admission.guard(), container.session_factory() as session:
            await SqlSourceControlRepository(session).set(
                SOURCE_ID, False, container.clock.now(), admin.id
            )
            await session.commit()

    async def guard(url):
        guarded.append(url)
        # DNS is mocked; no network or live-source acceptance.

    async def respond(request):
        calls.append(request)
        if disable_at == "during":
            await disable()
        data = payload(
            {"type": "Polygon", "coordinates": [[[0, 50], [1, 50], [1, 51], [0, 51], [0, 50]]]}
        )
        original = data["features"][0]
        data["features"] = []
        for name, at in [
            ("start", START),
            ("last", END - timedelta(microseconds=1)),
            ("end", END),
        ]:
            feature = deepcopy(original)
            feature["id"] = name
            feature["properties"]["datetime"] = at.isoformat()
            data["features"].append(feature)
        if disable_at == "outside":
            invalid = deepcopy(original)
            invalid["id"] = "outside"
            invalid["properties"]["datetime"] = (START - timedelta(microseconds=1)).isoformat()
            data["features"].append(invalid)
        return httpx.Response(200, json=data)

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        monkeypatch.setattr(container.http, "_client", transport)
        if disable_at == "before":
            await disable()
        response = await client.post(
            "/api/reports",
            headers=await headers(client, user),
            json={
                "template": "ask",
                "question": "Private area question",
                "research_mode": "quick",
                "research_source_ids": [SOURCE_ID],
                "research_terms": ["Private term"],
                "map_view_id": str(view.id),
                "map_revision_id": str(revision.id),
                "research_since": START.isoformat(),
                "research_until": END.isoformat(),
                "disclose_area_to_provider": True,
            },
        )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["report"]["scope"]["map_origin"]["revision_id"] == str(revision.id)
    assert result["report"]["id"] != str(parent.id)
    assert container.store.stats().total == 0
    assert len(calls) == len(guarded) == (0 if disable_at == "before" else 1)
    if calls:
        url = str(calls[0].url)
        assert urlsplit(url).hostname == "stac.dataspace.copernicus.eu"
        params = parse_qs(urlsplit(url).query)
        assert params["bbox"] == ["0.0,50.0,1.0,51.0"]
        assert params["datetime"] == ["2020-01-01T10:00:00.123456Z/2020-01-01T10:20:00.123457Z"]
        assert params["fields"] == ["-assets"]
        assert "Private" not in url
    evidence = result["version"]["evidence"]
    if disable_at == "never":
        assert {item["observation"]["item_id"] for item in evidence} == {"start", "last"}
        assert all(item["published_at"] is None and item["geometry"] for item in evidence)
        assert all(datetime.fromisoformat(item["captured_at"]) > END for item in evidence)
        drafts = [request for request in gateway.requests if request.schema_name == "report"]
        assert drafts
        prompt = "\n".join(message.content for message in drafts[0].messages)
        assert "Period: 2020-01-01 10:00 to 2020-01-01 10:20 UTC." in prompt
        assert f"Data cut-off: {container.clock.now():%Y-%m-%d %H:%M} UTC." in prompt
    else:
        assert evidence == []
