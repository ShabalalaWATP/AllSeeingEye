"""The GDELT events connector follows lastupdate.txt, unzips the export and codes rows."""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime

import pytest

from ase.adapters.feeds import gdelt_events
from ase.adapters.feeds.gdelt_events import (
    COLUMNS,
    MAX_EVENTS,
    GdeltEventsConnector,
    export_url,
    read_export,
)
from ase.adapters.feeds.http import FeedFetchError
from ase.domain.events import Category, Credibility, GeoConfidence
from feeds_helpers import NOW, FakeClock, FakeHttp

LISTING = (
    "38693 b5a65c13196621cd534b95182bd9ef02 "
    "http://data.gdeltproject.org/gdeltv2/20260905011500.export.CSV.zip\n"
    "66077 0a2e3efa345d2197c364483629c570be "
    "http://data.gdeltproject.org/gdeltv2/20260905011500.mentions.CSV.zip\n"
)
EXPORT = "https://data.gdeltproject.org/gdeltv2/20260905011500.export.CSV.zip"


def row(
    event_id: str = "1321563038",
    *,
    code: str = "190",
    root: str = "19",
    lat: str = "49.98",
    lon: str = "36.25",
    geo_type: str = "4",
    mentions: str = "12",
    sources: str = "4",
    goldstein: str = "-10.0",
    tone: str = "-6.5",
    url: str = "https://example.org/report",
) -> list[str]:
    cells = [""] * COLUMNS
    cells[0], cells[1], cells[6], cells[16] = event_id, "20260905", "UKRAINE", "RUSSIA"
    cells[26], cells[27], cells[28], cells[29] = code, code, root, "4"
    cells[30], cells[31], cells[32], cells[33], cells[34] = goldstein, mentions, sources, "3", tone
    cells[51], cells[52], cells[53] = geo_type, "Kharkiv, Kharkivs'ka Oblast', Ukraine", "UP"
    cells[56], cells[57], cells[59], cells[60] = lat, lon, "20260905011500", url
    return cells


def zipped(rows: list[list[str]], name: str = "20260905011500.export.CSV") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, "\n".join("\t".join(cells) for cells in rows) + "\n")
    return buffer.getvalue()


def http_for(rows: list[list[str]], listing: str = LISTING) -> FakeHttp:
    return FakeHttp({"lastupdate.txt": listing, "export.CSV.zip": zipped(rows)})


async def test_conflict_rows_become_graded_events() -> None:
    rows = [
        row(),
        row("2", code="141", root="14", geo_type="1", sources="1", goldstein="-6.5", tone="1.25"),
        row("3", root="04"),  # not a conflict code
        row("4", lat="", lon=""),  # unlocated
        row("5", lat="91", lon="0"),  # impossible latitude
        row("6", lat="abc", lon="1"),
        row("7", url="javascript:alert(1)", mentions="1"),
        row("1321563038", mentions="1"),  # duplicate id, fewer mentions
    ]
    http = http_for(rows)
    connector = GdeltEventsConnector(http, FakeClock(NOW))  # type: ignore[arg-type]
    events = await connector.fetch()
    assert http.requests == [gdelt_events.SPEC.url, EXPORT]
    assert [e.attributes["event_code"] for e in events] == ["190", "141", "190"]
    fight = events[0]
    assert fight.category is Category.CONFLICT and fight.subtype == "fight"
    assert fight.title == "Fighting: Ukraine and Russia, Kharkiv, Kharkivs'ka Oblast', Ukraine"
    assert fight.point is not None and (fight.point.lat, fight.point.lon) == (49.98, 36.25)
    assert fight.geo_confidence is GeoConfidence.CITY
    assert fight.severity == 1.0
    # Four sources can repeat one account; volume alone proves no independence.
    assert fight.credibility is Credibility.CANNOT_BE_JUDGED
    assert "independent" in fight.grade_rationale
    assert fight.published_at == datetime(2026, 9, 5, 1, 15, tzinfo=UTC)
    assert fight.url == "https://example.org/report"
    assert fight.attributes["mentions"] == 12 and fight.attributes["location_fips"] == "UP"
    assert "cameo_190" in fight.tags and "gdelt" in fight.tags
    assert fight.summary is not None and "12 mentions across 4 sources" in fight.summary
    protest = events[1]
    assert protest.subtype == "protest" and protest.severity == 0.65
    assert protest.credibility is Credibility.CANNOT_BE_JUDGED
    assert protest.geo_confidence is GeoConfidence.COUNTRY
    assert events[2].url is None
    # The same export is not ingested twice, and a new listing is followed.
    assert await connector.fetch() == []
    assert len(http.requests) == 3


async def test_listing_and_archive_faults() -> None:
    clock = FakeClock(NOW)
    with pytest.raises(FeedFetchError):
        await GdeltEventsConnector(http_for([row()], "no export here\n"), clock).fetch()  # type: ignore[arg-type]
    with pytest.raises(FeedFetchError):
        export_url("1 2 http://data.gdeltproject.org/gdeltv2/evil/../x.export.CSV.zip")
    assert export_url(LISTING) == EXPORT
    with pytest.raises(FeedFetchError):
        read_export(b"not a zip")
    two = io.BytesIO()
    with zipfile.ZipFile(two, "w") as archive:
        archive.writestr("a.csv", "x")
        archive.writestr("b.csv", "y")
    with pytest.raises(FeedFetchError):
        read_export(two.getvalue())
    assert await GdeltEventsConnector(FakeHttp(not_modified=True), clock).fetch() == []  # type: ignore[arg-type]


async def test_oversized_export_and_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gdelt_events, "MAX_CSV_BYTES", 10)
    with pytest.raises(FeedFetchError):
        read_export(zipped([row()]))
    monkeypatch.setattr(gdelt_events, "MAX_CSV_BYTES", 50 * 1024 * 1024)
    rows = [row(str(index), mentions=str(index)) for index in range(MAX_EVENTS + 25)]
    events = await GdeltEventsConnector(http_for(rows), FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert len(events) == MAX_EVENTS
    # Most-mentioned rows win when the batch is cut.
    assert events[0].attributes["mentions"] == MAX_EVENTS + 24
    short = read_export(zipped([["only", "two"]]))
    assert short == []
