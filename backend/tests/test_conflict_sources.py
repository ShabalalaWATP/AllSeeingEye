"""Provider fixtures verify event semantics and bounded, credential-local requests."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from ase.adapters.feeds.conflict_acled import AcledConnector
from ase.adapters.feeds.conflict_reliefweb import ReliefWebReportsConnector
from ase.adapters.feeds.conflict_ucdp import UcdpCandidateConnector
from ase.adapters.feeds.http import FeedFetchError, NotModified
from ase.domain.events import Category, Credibility, GeoConfidence
from feeds_helpers import NOW, FakeClock


class Http:
    def __init__(self, *payloads: Any) -> None:
        self.payloads = list(payloads)
        self.requests: list[tuple[str, dict[str, Any]]] = []

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        self.requests.append((url, kwargs))
        payload = self.payloads.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return payload


def ucdp(**changes: Any) -> dict[str, Any]:
    return {
        "id": 123,
        "type_of_violence": 1,
        "date_start": "2026-07-10",
        "date_end": "2026-07-11",
        "latitude": 49,
        "longitude": 35,
        "where_prec": 1,
        "where_coordinates": "Town",
        "country": "Ukraine",
        "side_a": "Actor A",
        "side_b": "Actor B",
        "low": 0,
        "best": 3,
        "high": 7,
        "source_article": "A syndicated report",
        "date_prec": 2,
        **changes,
    }


def acled(**changes: Any) -> dict[str, Any]:
    return {
        "event_id_cnty": "UKR123",
        "event_type": "Battles",
        "event_date": "2026-09-01",
        "latitude": 49,
        "longitude": 35,
        "geo_precision": 2,
        "time_precision": 1,
        "location": "Town",
        "country": "Ukraine",
        "fatalities": "0",
        "source": "A; B",
        **changes,
    }


async def test_ucdp_monthly_dates_ranges_credentials_and_duplicate_ids() -> None:
    http = Http(
        {"Result": [ucdp(), ucdp()], "TotalPages": 2, "NextPageUrl": "http://127.0.0.1/secret"},
        {"Result": [ucdp(id=124, type_of_violence=3, low=-1)], "TotalPages": 2},
    )
    connector = UcdpCandidateConnector(http, FakeClock(NOW), "fixture-token", "26.0.7")  # type: ignore[arg-type]
    events = await connector.fetch()
    assert len(events) == 2
    assert events[0].published_at is None
    assert events[0].observed_at == NOW
    assert events[0].attributes["occurrence_end"].startswith("2026-07-11")
    assert events[0].attributes["reported_fatalities_low"] == 0
    assert events[1].attributes["reported_fatalities_low"] is None
    assert events[1].subtype == "civilian_harm"
    assert events[0].geo_confidence == GeoConfidence.CITY
    assert events[0].credibility != Credibility.CONFIRMED
    assert events[0].subtype == "organised_violence"
    for url, kwargs in http.requests:
        assert url.startswith("https://ucdpapi.pcr.uu.se/api/gedevents/26.0.7?")
        assert "fixture-token" not in url
        query = parse_qs(urlsplit(url).query)
        assert query["StartDate"] == ["2026-07-01"]
        assert query["EndDate"] == ["2026-07-31"]
        assert kwargs["credential"].header_name == "x-ucdp-access-token"
        assert "fixture-token" not in repr(kwargs["credential"])


@pytest.mark.parametrize("version", ["latest", "26.1", "26.0.13", "26.0.0", "../secret"])
def test_ucdp_rejects_unpinned_or_invalid_candidate_versions(version: str) -> None:
    with pytest.raises(ValueError):
        UcdpCandidateConnector(Http(), FakeClock(NOW), "token", version)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"Result": [], "TotalPages": 21},
        {"Result": [], "TotalPages": 2},
        {"Result": [ucdp()] * 501, "TotalPages": 1},
    ],
)
async def test_ucdp_fails_explicitly_on_incomplete_or_unbounded_payload(payload: Any) -> None:
    with pytest.raises(FeedFetchError):
        await UcdpCandidateConnector(Http(payload), FakeClock(NOW), "token", "26.0.7").fetch()  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"id": None},
        {"type_of_violence": 9},
        {"date_start": "bad"},
        {"date_end": "2026-07-01"},
        {"date_end": "2026-08-01"},
        {"date_end": "2027-01-01"},
    ],
)
async def test_ucdp_invalid_rows_do_not_create_misdated_incidents(changes: dict[str, Any]) -> None:
    http = Http({"Result": [ucdp(**changes), 5], "TotalPages": 1})
    assert await UcdpCandidateConnector(http, FakeClock(NOW), "token", "26.0.7").fetch() == []  # type: ignore[arg-type]


async def test_ucdp_invalid_point_keeps_non_geographic_record_and_hash_changes() -> None:
    http = Http(
        {"Result": [ucdp(latitude="nan")], "TotalPages": 1},
        {"Result": [ucdp(latitude="nan", best=4)], "TotalPages": 1},
    )
    connector = UcdpCandidateConnector(http, FakeClock(NOW), "token", "26.0.7")  # type: ignore[arg-type]
    first, second = (await connector.fetch())[0], (await connector.fetch())[0]
    assert first.point is None and first.geo_confidence == GeoConfidence.NONE
    assert first.id == second.id and first.content_hash != second.content_hash


@pytest.mark.parametrize(
    ("event_type", "category", "subtype"),
    [
        ("Battles", Category.CONFLICT, "armed_clash"),
        ("Explosions/Remote violence", Category.CONFLICT, "strike"),
        ("Violence against civilians", Category.CONFLICT, "civilian_harm"),
        ("Protests", Category.CONFLICT, "protest"),
        ("Riots", Category.CONFLICT, "riot"),
        ("Strategic developments", Category.CONFLICT, "force_posture"),
    ],
)
async def test_acled_keeps_unrest_separate_and_does_not_invent_casualty_bounds(
    event_type: str,
    category: Category,
    subtype: str,
) -> None:
    http = Http({"status": 200, "data": [acled(event_type=event_type)]})
    event = (await AcledConnector(http, FakeClock(NOW), "fixture-token").fetch())[0]  # type: ignore[arg-type]
    assert (event.category, event.subtype) == (category, subtype)
    assert event.attributes["reported_fatalities_low"] is None
    assert event.attributes["reported_fatalities_best"] == 0
    assert event.attributes["fatalities_uncertain_zero"] is True
    assert "unknown" in event.attributes["fatalities_caveat"]
    assert event.published_at is None
    url, kwargs = http.requests[0]
    assert "fixture-token" not in url
    assert kwargs["credential"].authorization == "Bearer fixture-token"
    assert parse_qs(urlsplit(url).query)["export_type"] == ["dyadic"]


@pytest.mark.parametrize(
    "changes",
    [
        {"event_id_cnty": None},
        {"event_type": "Unknown"},
        {"event_date": "bad"},
        {"event_date": "2025-01-01"},
        {"event_date": "2027-01-01"},
    ],
)
async def test_acled_invalid_or_out_of_window_rows_skipped(changes: dict[str, Any]) -> None:
    http = Http({"status": 200, "data": [acled(**changes), None]})
    assert await AcledConnector(http, FakeClock(NOW), "token").fetch() == []  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"status": 403, "error": "secret"},
        {"status": 200, "data": {}},
        {"status": 200, "data": [acled()] * 501},
    ],
)
async def test_acled_entitlement_and_size_errors_are_safe(payload: Any) -> None:
    with pytest.raises(FeedFetchError) as error:
        await AcledConnector(Http(payload), FakeClock(NOW), "token").fetch()  # type: ignore[arg-type]
    assert "secret" not in str(error.value)


async def test_acled_cap_is_explicit_and_never_follows_upstream_pagination(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr("ase.adapters.feeds.conflict_acled.PAGE_SIZE", 1)
    monkeypatch.setattr("ase.adapters.feeds.conflict_acled.MAX_PAGES", 2)
    http = Http(*[{"status": 200, "data": [acled()], "next": "http://localhost"}] * 2)
    with pytest.raises(FeedFetchError, match="incomplete"):
        await AcledConnector(http, FakeClock(NOW), "token").fetch()  # type: ignore[arg-type]
    assert len(http.requests) == 2


def report(**changes: Any) -> dict[str, Any]:
    return {
        "id": "123",
        "fields": {
            "title": "Displacement report",
            "date": {"original": "2026-09-01T12:00:00Z", "created": "2026-09-02"},
            "url": "https://reliefweb.int/report/ukraine/example",
            "origin": "https://publisher.test/report",
            "source": [{"name": "Original NGO"}],
            "primary_country": {"name": "Ukraine", "iso3": "UKR"},
            "country": [{"name": "Ukraine"}],
            **changes,
        },
    }


async def test_reliefweb_keeps_publisher_context_and_no_false_location() -> None:
    http = Http({"data": [report(), report()]})
    connector = ReliefWebReportsConnector(http, FakeClock(NOW), "approved-fixture", {"UKR": "UA"})  # type: ignore[arg-type]
    events = await connector.fetch()
    assert len(events) == 1
    event = events[0]
    assert event.category == Category.HUMANITARIAN and event.point is None
    assert event.country_iso == "UA"
    assert event.attributes["original_publishers"] == "Original NGO"
    assert event.attributes["original_url"] == "https://publisher.test/report"
    assert event.credibility == Credibility.CANNOT_BE_JUDGED
    query = parse_qs(urlsplit(http.requests[0][0]).query)
    assert query["limit"] == ["100"] and query["preset"] == ["latest"]
    assert "body" not in query["fields[include][]"]


@pytest.mark.parametrize("appname", ["", "x", "bad name", "?fake=1", "a" * 101])
def test_reliefweb_requires_valid_application_name(appname: str) -> None:
    with pytest.raises(ValueError):
        ReliefWebReportsConnector(Http(), FakeClock(NOW), appname)  # type: ignore[arg-type]


async def test_reliefweb_partial_fields_and_untrusted_links() -> None:
    http = Http(
        {
            "data": [
                report(
                    primary_country=[],
                    source=None,
                    country=None,
                    url="javascript:alert(1)",
                    origin="https://user:pass@host/",
                    date=None,
                ),
                {"id": 2},
                None,
            ]
        }
    )
    event = (await ReliefWebReportsConnector(http, FakeClock(NOW), "approved").fetch())[0]  # type: ignore[arg-type]
    assert event.url is None and event.published_at is None
    assert event.attributes["original_url"] is None
    assert event.geo_confidence == GeoConfidence.NONE


@pytest.mark.parametrize("payload", [None, {}, {"data": [report()] * 101}])
async def test_reliefweb_rejects_bad_envelope(payload: Any) -> None:
    with pytest.raises(FeedFetchError):
        await ReliefWebReportsConnector(Http(payload), FakeClock(NOW), "approved").fetch()  # type: ignore[arg-type]


async def test_reliefweb_conditional_304_is_no_change() -> None:
    assert (
        await ReliefWebReportsConnector(
            Http(NotModified("url")), FakeClock(NOW), "approved"
        ).fetch()
        == []
    )  # type: ignore[arg-type]


def test_polling_is_polite() -> None:
    assert UcdpCandidateConnector(
        Http(), FakeClock(NOW), "token", "26.0.7"
    ).spec.poll_interval >= timedelta(days=1)  # type: ignore[arg-type]
    assert AcledConnector.spec.poll_interval >= timedelta(hours=6)
    assert ReliefWebReportsConnector.spec.poll_interval >= timedelta(hours=1)
