"""Exact file references, inert extraction and reproducible character citations."""

import hashlib
from dataclasses import replace
from datetime import date

import pytest

from ase.adapters.research_records.sec_document import MAX_TEXT, document_url, extract
from ase.adapters.research_records.sec_history import rows
from ase.domain.events import Credibility, Reliability
from ase.domain.sec_filings import SecFiling
from research_records_helpers import CLOCK
from sec_filings_helpers import CIK, DOCUMENT, columns

FILING = SecFiling(
    CIK, "0000999999-26-000001", "filing.htm", "10-K", date(2026, 8, 31), "Synthetic Issuer"
)


def test_visible_text_locations_original_hash_and_unassessed_assertions() -> None:
    raw = (
        b'<html><head>Hidden title</head><body><script>fetch("http://private")</script>'
        b"<p>Revenue &amp; costs.</p><div hidden>Secret</div><table><tr><td>12</td>"
        b"<td>GBP</td></tr></table><ix:hidden>Hidden fact</ix:hidden></body></html>"
    )
    result = extract(raw, FILING, CLOCK.now())
    assert result.sha256 == hashlib.sha256(raw).hexdigest()
    assert result.events[0].summary == "Revenue & costs. 12 GBP"
    event = result.events[0]
    assert event.url == document_url(FILING) == DOCUMENT
    assert event.source_id == "research_import"
    assert event.reliability is Reliability.F
    assert event.credibility is Credibility.CANNOT_BE_JUDGED
    assert event.attributes["original_sha256"] == result.sha256
    assert event.attributes["text_start"] == 0
    assert event.attributes["text_end"] == len(event.summary)
    assert event.published_at is None
    assert event.attributes["filing_date"] == FILING.filing_date.isoformat()
    assert event.observed_at == CLOCK.now()
    assert any("transiently" in value for value in result.limitations)


def test_long_text_has_bounded_contiguous_citations_and_explicit_truncation() -> None:
    raw = b"word " * 25000
    result = extract(raw, replace(FILING, primary_document="filing.txt"), CLOCK.now())
    assert len(result.events) == 80
    assert result.events[-1].attributes["text_end"] == MAX_TEXT
    assert all(event.attributes["text_truncated"] for event in result.events)
    assert result.events[1].attributes["text_start"] == 1400
    assert any("truncated" in line for line in result.limitations)


@pytest.mark.parametrize(
    "document",
    ["../a.htm", "a..htm", "https://evil/a.htm", "a%2f.htm", 'a".htm', "a.pdf", "a.htm?x=1"],
)
def test_primary_document_cannot_be_a_path_or_arbitrary_resource(document: str) -> None:
    with pytest.raises(ValueError, match="reference"):
        replace(FILING, primary_document=document)
    data = columns()
    data["primaryDocument"] = [document]
    assert rows(data, CIK, "Issuer", date(2020, 1, 1), date(2026, 9, 1)) == []


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"a\x00b",
        b"x" * (4 * 1024 * 1024 + 1),
        b"<script>Only script</script>",
        b"Your request originates from an undeclared automated tool",
    ],
    ids=["empty", "binary", "oversize", "hidden", "blocked"],
)
def test_unsupported_or_policy_response_is_not_successful_content(raw: bytes) -> None:
    with pytest.raises(ValueError):
        extract(raw, FILING, CLOCK.now())


def test_legacy_encoding_and_markup_complexity_are_explicit() -> None:
    result = extract(b"<p>Revenue \xa3 12</p>", FILING, CLOCK.now())
    assert result.events[0].summary == "Revenue £ 12"
    assert result.events[0].attributes["text_encoding"] == "windows-1252"
    with pytest.raises(ValueError, match="complexity"):
        extract(b"<b>" * 100001, FILING, CLOCK.now())
