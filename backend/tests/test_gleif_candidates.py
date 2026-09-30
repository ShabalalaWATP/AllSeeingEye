"""Public name lookup is bounded and does not confirm ambiguous identities."""

from typing import Any
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import pytest

from ase.adapters.research_records.gleif_candidates import GleifCandidates
from ase.domain.errors import InvalidRequest

LEI = "5493001KJTIIGC8Y1R12"


def record() -> dict[str, Any]:
    return {
        "id": LEI,
        "attributes": {
            "lei": LEI,
            "entity": {
                "legalName": {"name": "Example Limited"},
                "jurisdiction": "GB",
                "status": "ACTIVE",
                "legalAddress": {"country": "GB"},
            },
        },
    }


async def test_one_request_preserves_candidate_fields_and_does_not_follow_links() -> None:
    http = AsyncMock()
    http.get_json.return_value = {"data": [record()], "links": {"next": "https://elsewhere"}}
    rows = await GleifCandidates(http).search("Example, Limited", "GB")
    assert [(row.lei, row.name, row.jurisdiction, row.status) for row in rows] == [
        (LEI, "Example Limited", "GB", "ACTIVE"),
    ]
    http.get_json.assert_awaited_once()
    url = http.get_json.call_args.args[0]
    assert urlsplit(url).hostname == "api.gleif.org"
    assert parse_qs(urlsplit(url).query) == {
        "filter[entity.legalName]": ["Example  Limited"],
        "page[size]": ["10"],
        "filter[entity.legalAddress.country]": ["GB"],
    }


async def test_empty_oversized_and_country_mismatch_are_bounded() -> None:
    http = AsyncMock()
    http.get_json.return_value = {"data": []}
    assert await GleifCandidates(http).search("Example", None) == ()
    http.get_json.return_value = {"data": [record()] * 11 + [None]}
    assert len(await GleifCandidates(http).search("Example", None)) == 1
    assert await GleifCandidates(http).search("Example", "US") == ()


@pytest.mark.parametrize("payload", [None, {"data": None}, {"data": [{}]}])
async def test_invalid_payload_never_becomes_a_candidate(payload: Any) -> None:
    http = AsyncMock()
    http.get_json.return_value = payload
    with pytest.raises(InvalidRequest):
        await GleifCandidates(http).search("Example", None)
