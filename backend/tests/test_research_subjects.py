"""Synthetic HTTP responses only; bounded routing and unverified signals remain explicit."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import pytest

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.research_subjects.parliament import ParliamentQuestionsProvider
from ase.adapters.research_subjects.scholarly import CrossrefProvider, OpenAlexProvider
from ase.adapters.research_subjects.specs import subject_specs
from ase.adapters.research_subjects.world_bank import WorldBankProvider, indicator_subject
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchQuery
from helpers import FakeClock

NOW = datetime(2026, 8, 10, tzinfo=UTC)
QUERY = ResearchQuery(
    "PRIVATE research question",
    NOW - timedelta(days=5),
    NOW,
    terms=("explicit public phrase",),
    subject="academic:",
)


def client(payload=None, error=None):
    http = AsyncMock(spec=FeedHttpClient)
    http.get_json.return_value = payload
    http.get_json.side_effect = error
    return http


@pytest.mark.parametrize(
    "provider_type", [OpenAlexProvider, CrossrefProvider, ParliamentQuestionsProvider]
)
async def test_opt_in_and_explicit_terms_required_before_request(provider_type) -> None:
    http = client()
    provider = provider_type(http, FakeClock(NOW))
    ordinary = replace(QUERY, subject=None)
    assert not provider.supports(ordinary)
    assert (await provider.collect(ordinary)).attempts[0].status is CollectionStatus.UNSUPPORTED
    assert provider.supports(replace(ordinary, source_ids=(provider.id,)))
    assert not provider.supports(replace(ordinary, source_ids=(provider.id,), terms=()))
    assert not provider.supports(
        replace(ordinary, source_ids=(provider.id,), focus=ResearchFocus.DOCUMENT)
    )
    assert not provider.supports(replace(ordinary, source_ids=(provider.id,), country_iso="FR"))
    http.get_json.assert_not_called()


async def test_openalex_one_request_fixed_origin_signals_dates_and_bad_ids() -> None:
    row = {
        "id": "https://openalex.org/W123",
        "display_name": "Synthetic paper",
        "doi": None,
        "publication_date": "2026-08-07",
        "is_retracted": True,
    }
    http = client(
        {
            "results": [
                row,
                row,
                {**row, "id": "http://127.0.0.1/"},
                {**row, "id": "https://openalex.org/W2", "publication_date": "2020-01-01"},
            ]
        }
    )
    result = await OpenAlexProvider(http, FakeClock(NOW)).collect(QUERY)
    assert len(result.items) == 1
    assert result.items[0].attributes["retraction_signal"] == "reported"
    assert result.items[0].credibility.value == 6
    assert result.items[0].grade == "F6"
    assert "not establish integrity" in result.items[0].summary
    args, kwargs = http.get_json.call_args
    assert http.get_json.call_count == 1
    assert urlsplit(args[0]).hostname == "api.openalex.org"
    assert "PRIVATE" not in args[0]
    assert parse_qs(urlsplit(args[0]).query)["search"] == ["explicit public phrase"]
    assert kwargs == {"conditional": False, "max_redirects": 0}


@pytest.mark.parametrize(
    "flag,expected", [(False, "not_reported"), (None, "unknown"), ("false", "unknown")]
)
async def test_missing_retraction_flag_is_not_integrity_clearance(flag, expected) -> None:
    http = client(
        {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "display_name": "Synthetic",
                    "publication_date": "2026-08-07",
                    "is_retracted": flag,
                }
            ]
        }
    )
    result = await OpenAlexProvider(http, FakeClock(NOW)).collect(QUERY)
    assert result.items[0].attributes["retraction_signal"] == expected


async def test_crossref_notice_target_remains_distinct_and_incomplete_dates_excluded() -> None:
    row = {
        "DOI": "10.1234/notice",
        "title": ["Synthetic notice"],
        "published": {"date-parts": [[2026, 8, 7]]},
        "update-to": [{"DOI": "10.1234/original", "type": "retraction", "source": "publisher"}],
    }
    http = client(
        {
            "message": {
                "items": [
                    row,
                    {**row, "DOI": "10.1234/year", "published": {"date-parts": [[2026]]}},
                ]
            }
        }
    )
    result = await CrossrefProvider(http, FakeClock(NOW)).collect(QUERY)
    assert len(result.items) == 1
    event = result.items[0]
    assert event.grade == "F6"
    assert event.attributes["doi"] == "10.1234/notice"
    assert "targets 10.1234/original" in event.summary
    assert event.attributes["retraction_status"] == "not_determined"
    assert event.url == "https://doi.org/10.1234/notice"
    assert http.get_json.call_count == 1


@pytest.mark.parametrize(
    "value",
    [
        None,
        "GB GDP",
        "WB:GB;US:X:2020:2024",
        "WB:GB:../x:2020:2024",
        "WB:GB:X:2024:2020",
        "WB:GB:AA:1900:2020",
        "WB:GB:AA:1800:1801",
    ],
)
def test_indicator_subject_rejects_fanout_paths_and_unbounded_years(value) -> None:
    assert indicator_subject(value) is None


async def test_world_bank_preserves_missing_zero_unit_and_period_not_publication_year() -> None:
    row = {
        "country": {"id": "GB"},
        "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP"},
        "date": "2024",
        "value": None,
        "unit": "",
    }
    http = client(
        [
            {"lastupdated": "2026-08-01"},
            [
                row,
                {**row, "date": "2023", "value": 0},
                {**row, "date": "2022", "value": True},
                {**row, "date": "2021", "value": float("nan")},
                {**row, "country": {"id": "US"}},
            ],
        ]
    )
    query = replace(QUERY, subject="WB:GB:NY.GDP.MKTP.CD:2020:2024", country_iso="GB")
    result = await WorldBankProvider(http, FakeClock(NOW)).collect(query)
    assert len(result.items) == 2
    assert all(event.grade == "F6" for event in result.items)
    assert result.items[0].attributes["missing_value"] is True
    assert result.items[0].attributes["value"] is None
    assert result.items[0].attributes["unit"] is None
    assert result.items[1].attributes["value"] == 0
    assert result.items[1].attributes["missing_value"] is False
    assert result.items[0].published_at == NOW
    assert result.items[0].attributes["observation_year"] == "2024"
    assert http.get_json.call_count == 1
    assert urlsplit(http.get_json.call_args.args[0]).hostname == "api.worldbank.org"
    assert not WorldBankProvider(http, FakeClock(NOW)).supports(
        replace(query, country_iso="US", country_isos=())
    )


async def test_parliament_current_attributed_answer_and_correction_no_followed_links() -> None:
    row = {
        "value": {
            "id": 12,
            "dateTabled": "2026-08-07T00:00:00",
            "questionText": "<p>Question?</p>",
            "heading": "Synthetic subject",
            "answerText": "<p>Attributed answer.</p>",
            "answerIsCorrection": True,
            "isWithdrawn": None,
        },
        "links": [{"href": "http://127.0.0.1/secret"}],
    }
    http = client({"results": [row]})
    result = await ParliamentQuestionsProvider(http, FakeClock(NOW)).collect(
        replace(QUERY, subject="parliament:")
    )
    assert len(result.items) == 1 and http.get_json.call_count == 1
    assert result.items[0].grade == "F6"
    assert result.items[0].attributes["answer_correction"] is True
    assert result.items[0].attributes["withdrawn"] is None
    assert "Withdrawn: unknown" in result.items[0].summary
    assert "<p>" not in result.items[0].summary
    assert (
        urlsplit(http.get_json.call_args.args[0]).hostname
        == "questions-statements-api.parliament.uk"
    )


@pytest.mark.parametrize(
    "provider_type,subject",
    [
        (OpenAlexProvider, "academic:"),
        (CrossrefProvider, "academic:"),
        (WorldBankProvider, "WB:GB:AA:2020:2024"),
        (ParliamentQuestionsProvider, "parliament:"),
    ],
)
@pytest.mark.parametrize(
    "error,status",
    [
        (FeedFetchError("PRIVATE upstream body"), CollectionStatus.FAILED),
        (TimeoutError(), CollectionStatus.TIMED_OUT),
    ],
)
async def test_safe_error_receipts_and_no_retry(provider_type, subject, error, status) -> None:
    http = client(error=error)
    batch = await provider_type(http, FakeClock(NOW)).collect(replace(QUERY, subject=subject))
    assert batch.attempts[0].status is status
    assert "PRIVATE" not in batch.attempts[0].explanation
    assert http.get_json.call_count == 1


def test_registry_does_not_claim_independence_for_overlapping_scholarly_aggregators() -> None:
    specs = subject_specs()
    assert len({spec.id for spec in specs}) == 4
    assert all(spec.independence_key == "" for spec in specs[:2])
    assert all(
        spec.reliability.value == "F" and spec.rating.status == "unassessed" for spec in specs
    )
    assert all(not spec.rating.publisher_reliability_assessed for spec in specs)
    assert all(spec.url == spec.homepage == "" for spec in specs)


async def test_oversized_scholarly_response_does_not_expand_request_or_item_budget() -> None:
    http = client(
        {
            "results": [
                {
                    "id": f"https://openalex.org/W{index}",
                    "display_name": "Synthetic work",
                    "publication_date": "2026-08-07",
                }
                for index in range(100)
            ]
        }
    )
    result = await OpenAlexProvider(http, FakeClock(NOW)).collect(QUERY)
    assert len(result.items) == 20
    assert result.attempts[0].result_count == 20
    assert http.get_json.call_count == 1


@pytest.mark.parametrize(
    "provider_type,subject",
    [
        (OpenAlexProvider, "academic:"),
        (CrossrefProvider, "academic:"),
        (WorldBankProvider, "WB:GB:AA:2020:2024"),
        (ParliamentQuestionsProvider, "parliament:"),
    ],
)
async def test_malformed_response_is_not_an_empty_success(provider_type, subject) -> None:
    http = client({"upstream_error": "PRIVATE response"})
    result = await provider_type(http, FakeClock(NOW)).collect(replace(QUERY, subject=subject))
    assert result.attempts[0].status is CollectionStatus.FAILED
    assert "PRIVATE" not in result.attempts[0].explanation
