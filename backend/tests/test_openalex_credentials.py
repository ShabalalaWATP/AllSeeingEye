"""OpenAlex credentials stay request-local and do not expand research admission."""

from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.adapters.research_subjects.scholarly import OpenAlexProvider
from ase.domain.research import CollectionStatus
from research_records_helpers import CLOCK, QUERY, RecordService

KEY = "synthetic-openalex-test-key"
ACADEMIC = replace(QUERY, terms=("satellite research",), source_ids=("research-openalex",))
PAYLOAD = {
    "results": [
        {
            "id": "https://openalex.org/W123",
            "display_name": "Synthetic publication",
            "publication_date": "2026-09-05",
        }
    ]
}


@pytest.mark.parametrize("key", [None, "", KEY])
async def test_optional_key_is_header_only_and_does_not_leak_to_other_sources(
    monkeypatch: pytest.MonkeyPatch, key: str | None
) -> None:
    service = RecordService(monkeypatch, PAYLOAD)
    try:
        provider = OpenAlexProvider(service.http, CLOCK, api_key=key)
        result = await provider.collect(ACADEMIC)
        await service.http.get_json("https://api.crossref.org/works", conditional=False)
        request, other = service.requests
        assert request.url.host == "api.openalex.org"
        assert request.url.params["per_page"] == "20"
        assert request.headers.get("authorization") == (f"Bearer {key}" if key else None)
        assert "authorization" not in other.headers
        assert "api_key" not in request.url.params
        assert KEY not in str(request.url) and KEY not in repr(result)
        assert len(result.items) == 1 and result.items[0].grade == "F6"
        assert ("Authenticated" if key else "Anonymous") in result.attempts[0].explanation
        assert len(service.guarded) == 2
    finally:
        await service.http.aclose()


@pytest.mark.parametrize("status", [302, 401, 403, 429, 500])
async def test_authenticated_failure_is_not_retried_anonymously_or_redirected(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    service = RecordService(
        monkeypatch,
        response=httpx.Response(
            status, text=KEY, headers={"location": "https://other.example/steal"}
        ),
    )
    try:
        result = await OpenAlexProvider(service.http, CLOCK, api_key=KEY).collect(ACADEMIC)
        assert result.attempts[0].status is CollectionStatus.FAILED
        assert len(service.requests) == 1
        assert KEY not in repr(result)
    finally:
        await service.http.aclose()


@pytest.mark.parametrize("key", ["bad\nkey", "bad key", "ü", "x" * 513])
async def test_invalid_key_is_rejected_without_disclosing_it(
    monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    service = RecordService(monkeypatch)
    try:
        with pytest.raises(ValueError, match="OpenAlex API key configuration") as error:
            OpenAlexProvider(service.http, CLOCK, api_key=key)
        assert key not in str(error.value)
        assert not service.requests
    finally:
        await service.http.aclose()


@pytest.fixture
def settings(settings):
    settings.openalex_api_key = SecretStr(KEY)
    return settings


@pytest.mark.parametrize("disabled", [False, True])
async def test_production_composition_passes_secret_and_keeps_source_admission(
    container, admin, monkeypatch, disabled
) -> None:
    now = container.clock.now()
    query = replace(ACADEMIC, since=now - timedelta(days=1), until=now)
    calls = []

    async def get_json(self, url, **kwargs):
        calls.append((url, kwargs))
        return {"results": []}

    monkeypatch.setattr(FeedHttpClient, "get_json", get_json)
    if disabled:
        async with container.source_admission.guard(), container.session_factory() as session:
            await SqlSourceControlRepository(session).set("research-openalex", False, now, admin.id)
            await session.commit()
    assert KEY not in repr(container.settings)
    result = await container.research.collect(query)
    assert len(calls) == (0 if disabled else 1)
    assert KEY not in repr(result)
    if not disabled:
        credential = calls[0][1]["credential"]
        assert credential.origin == "https://api.openalex.org"
        assert credential.authorization == f"Bearer {KEY}"
        assert KEY not in repr(credential)
        assert result.attempts[0].status is CollectionStatus.EMPTY
    assert container.store.stats().total == 0
