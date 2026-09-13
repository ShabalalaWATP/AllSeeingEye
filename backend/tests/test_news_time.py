"""Only source-specified indexing metadata supplies the separate News map clock."""

from dataclasses import replace

import pytest

from ase.application.reports.reference_projection import build_references, reference_text
from ase.domain.events import Category
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_time import EvidenceTimeBasis, MapTimeBasis, evidence_time
from ase.domain.news_time import news_index_date, news_indexing_time
from feeds_helpers import NOW, make_event


@pytest.mark.parametrize("raw", ["", "bad", "20260913250000", "2026091", "20260230120000"])
def test_invalid_index_dates_stay_unknown(raw):
    date = news_index_date(raw)
    assert date.value is None and date.status == "invalid"


def test_map_time_requires_matching_typed_metadata_without_changing_evidence_dates():
    date = news_index_date(NOW.strftime("%Y%m%d%H%M%S"))
    event = make_event(category=Category.NEWS, published_at=None).with_changes(
        source_id="gdelt_news", source_dates=(date,)
    )
    assert news_indexing_time(event) == NOW
    assert evidence_time(event, MapTimeBasis.MAP) == NOW
    with pytest.raises(ValueError):
        EvidenceTimeBasis("map_record_time")
    assert evidence_time(event, EvidenceTimeBasis.PUBLICATION) is None
    assert evidence_time(event, EvidenceTimeBasis.RESEARCH) is None
    assert news_indexing_time(event.with_changes(source_dates=())) is None
    assert news_indexing_time(event.with_changes(source_id="some_rss")) is None
    assert news_indexing_time(event.with_changes(category=Category.CONFLICT)) is None
    for changed in (replace(date, role="publication"), replace(date, raw_text="20250101000000")):
        assert news_indexing_time(event.with_changes(source_dates=(changed,))) is None


def test_frozen_report_references_do_not_present_indexing_time_as_publication():
    date = news_index_date(NOW.strftime("%Y%m%d%H%M%S"))
    event = make_event(category=Category.NEWS, published_at=None).with_changes(
        source_id="gdelt_news", source_dates=(date,)
    )
    evidence = EvidenceItem.from_event("E1", event, NOW, source_name="GDELT", independence_key="")
    reference = build_references({"E1": 1}, {"E1": evidence})[0]
    assert reference.published_at is None
    assert "date not reported" in reference_text(reference)
    assert evidence.source_dates == (date,)
