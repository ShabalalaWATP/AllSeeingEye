"""Public UCDP downloads stay bounded and keep monthly occurrence provenance."""

import csv
import io
from typing import Any

import pytest

from ase.adapters.feeds.conflict_ucdp_public import UcdpPublicCandidateConnector
from ase.adapters.feeds.conflict_values import count, integer, public_link, when
from ase.adapters.feeds.http import FeedFetchError
from feeds_helpers import NOW, FakeClock, FakeHttp


def csv_rows(*changes: dict[str, Any]) -> str:
    data = io.StringIO()
    writer = csv.DictWriter(
        data,
        fieldnames=[
            "id",
            "date_start",
            "date_end",
            "type_of_violence",
            "latitude",
            "longitude",
            "low",
            "best",
            "high",
            "where_prec",
        ],
    )
    writer.writeheader()
    for change in changes or [{}]:
        writer.writerow(
            {
                "id": "123",
                "date_start": "2026-07-11 00:00:00.000",
                "date_end": "2026-07-12 00:00:00.000",
                "type_of_violence": "1",
                "latitude": "49",
                "longitude": "35",
                "low": "1",
                "best": "2",
                "high": "3",
                "where_prec": "1",
                **change,
            }
        )
    return data.getvalue()


async def test_public_download_shares_stable_id_and_provenance() -> None:
    http = FakeHttp({".csv": "\ufeff" + csv_rows({}, {}, {"id": "124"})})
    connector = UcdpPublicCandidateConnector(http, FakeClock(NOW), "26.0.7")  # type: ignore[arg-type]
    events = await connector.fetch()
    assert len(events) == 2
    assert connector.spec.id == "ucdp_candidate" and not connector.spec.requires_key
    assert http.requests == ["https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_0_7.csv"]
    assert events[0].attributes["origin_dataset"] == "ucdp_ged"
    assert events[0].attributes["incident_id"] == "123"
    assert events[0].attributes["coverage_end"] == "2026-07-31"
    assert events[0].published_at is None
    assert events[0].subtype == "organised_violence"
    assert events[0].attributes["reported_fatalities_low"] == 1


async def test_public_download_conditional_no_change() -> None:
    http = FakeHttp(not_modified=True)
    assert await UcdpPublicCandidateConnector(http, FakeClock(NOW), "26.0.7").fetch() == []  # type: ignore[arg-type]


async def test_daily_refresh_preserves_incident_dates() -> None:
    class DailyHttp:
        async def get_text(self, url: str, *, conditional: bool = True) -> str:
            assert conditional is False
            return csv_rows()

    connector = UcdpPublicCandidateConnector(DailyHttp(), FakeClock(NOW), "26.0.7")  # type: ignore[arg-type]
    first, second = await connector.fetch(), await connector.fetch()
    assert first[0].id == second[0].id
    assert first[0].attributes["occurrence_start"] == second[0].attributes["occurrence_start"]


@pytest.mark.parametrize("data", ["<html>Error</html>", "id,other\n1,bad\n"])
async def test_public_download_rejects_error_pages(data: str) -> None:
    with pytest.raises(FeedFetchError, match="required columns"):
        await UcdpPublicCandidateConnector(
            FakeHttp({".csv": data}), FakeClock(NOW), "26.0.7"
        ).fetch()  # type: ignore[arg-type]


async def test_public_download_has_explicit_row_bound(monkeypatch: Any) -> None:
    monkeypatch.setattr("ase.adapters.feeds.conflict_ucdp_public.MAX_ROWS", 1)
    with pytest.raises(FeedFetchError, match="capacity"):
        await UcdpPublicCandidateConnector(
            FakeHttp({".csv": csv_rows({}, {})}), FakeClock(NOW), "26.0.7"
        ).fetch()  # type: ignore[arg-type]


async def test_public_download_yields_and_skips_bad_rows() -> None:
    http = FakeHttp({".csv": csv_rows(*[{}] * 250, {"date_start": "bad"})})
    assert len(await UcdpPublicCandidateConnector(http, FakeClock(NOW), "26.0.7").fetch()) == 1  # type: ignore[arg-type]


async def test_public_download_rejects_oversize_csv_fields() -> None:
    data = csv_rows({"id": "1" * 200_000})
    with pytest.raises(FeedFetchError, match="invalid field"):
        await UcdpPublicCandidateConnector(
            FakeHttp({".csv": data}), FakeClock(NOW), "26.0.7"
        ).fetch()  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, "nan", "inf", "1.5", {}, None])
def test_invalid_count_is_unknown_not_zero(value: Any) -> None:
    assert count(value) is None


def test_counts_and_links_are_constrained() -> None:
    assert count("-1") is None and count("0") == 0
    assert integer("1e999") is None
    assert public_link("https://[bad/") is None
    assert when("9999-12-31T23:00:00-23:00") is None


async def test_upstream_errors_propagate_without_successful_empty_feed() -> None:
    class BrokenHttp:
        async def get_text(self, url: str, *, conditional: bool = True) -> str:
            raise FeedFetchError("unavailable")

    with pytest.raises(FeedFetchError, match="unavailable"):
        await UcdpPublicCandidateConnector(BrokenHttp(), FakeClock(NOW), "26.0.7").fetch()  # type: ignore[arg-type]
