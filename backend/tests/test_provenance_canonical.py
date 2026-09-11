"""Pin canonical hashes measured on pre-provenance main 0c91741, including comparison bytes."""

import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest

import report_documents_helpers as fixtures
from annotation_comparison_helpers import side
from ase.application.reports.claim_export_integrity import export_content_digest
from ase.application.reports.comparison_manifest import comparison_digest, comparison_json
from ase.domain.annotation_comparison import COMPARISON_METHOD, AnnotationComparison
from ase.domain.canonical_provenance import canonical_snapshot
from ase.domain.research_records import research_from_dict
from ase.domain.sec_filing_time import filing_source_date
from ase.domain.source_dates import resolve_source_date
from ase.domain.web_research import WebResearchRecord


def records(monkeypatch):
    ids = iter([UUID(int=10), UUID(int=11)])
    monkeypatch.setattr(fixtures, "uuid4", lambda: next(ids))
    return fixtures.document_records(UUID(int=1))


def comparison(version):
    return AnnotationComparison(
        COMPARISON_METHOD,
        version.created_at,
        "",
        UUID(int=1),
        side(version),
        side(version),
        (),
        (),
        (),
        (),
        (),
    )


def test_historical_export_and_comparison_hashes_are_unchanged(monkeypatch):
    record, version = records(monkeypatch)
    assert (
        export_content_digest(record, version)
        == "ab43e8fbe48ab4b3ffd929d78ef89931889b35d1d1831b68caba04e93ba40641"
    )
    value = comparison(version)
    assert (
        comparison_digest(value)
        == "e6b39b543363730afb700839a3b0c297711f94bd34c40b33aeb342e52d1e9978"
    )
    assert len(comparison_json(value)) == 13042


@pytest.mark.parametrize(
    "source_date",
    [
        resolve_source_date("1404-01-01", "summary", "solar_hijri_icu33"),
        filing_source_date("2025-03-21"),
    ],
)
def test_real_day_metadata_is_included_in_both_digests_and_manifest(monkeypatch, source_date):
    record, version = records(monkeypatch)
    old = export_content_digest(record, version)
    dated = replace(
        version.evidence[0],
        source_dates=(source_date,),
    )
    changed = replace(version, evidence=(dated, *version.evidence[1:]))
    assert export_content_digest(record, changed) != old
    assert comparison_digest(comparison(changed)) != comparison_digest(comparison(version))
    manifest = json.loads(comparison_json(comparison(changed)))
    assert manifest["before"]["evidence"][0]["source_dates"][0]["day_start"] == "2025-03-21"


def test_historical_nested_query_trace_digest_survives_new_variant_fields(monkeypatch):
    record, version = records(monkeypatch)
    payload = json.loads(
        (Path(__file__).parent / "fixtures/provenance_legacy_research.json").read_text(
            encoding="utf-8"
        )
    )
    restored = replace(version, research=research_from_dict(payload))
    assert (
        export_content_digest(record, restored)
        == "c4607ec62bd4ccb7b18798863400362f52bd7f7000ffe8740066e10f6be49757"
    )


def test_nondefault_research_scope_and_web_choices_remain_bound_in_digest(monkeypatch):
    record, version = records(monkeypatch)
    payload = json.loads(
        (Path(__file__).parent / "fixtures/provenance_legacy_research.json").read_text(
            encoding="utf-8"
        )
    )
    receipt = research_from_dict(payload)
    original = replace(version, research=receipt)
    original_digest = export_content_digest(record, original)
    variants = (
        replace(receipt, plan=replace(receipt.plan, country_isos=("UA", "RU"))),
        replace(receipt, plan=replace(receipt.plan, research_web_search=True)),
        replace(
            receipt,
            web_research=WebResearchRecord("unavailable", "Provider unavailable", receipt.until),
        ),
    )
    digests = {
        export_content_digest(record, replace(version, research=variant)) for variant in variants
    }
    assert len(digests) == 3 and original_digest not in digests
    # Default omission applies to the named domain records, never arbitrary metadata.
    metadata = {"web_research": None, "country_isos": (), "research_web_search": False}
    assert canonical_snapshot(metadata) == metadata


def test_historical_single_country_digest_survives_redundant_plural_scope(monkeypatch):
    record, version = records(monkeypatch)
    payload = json.loads(
        (
            Path(__file__).parent / "fixtures/provenance_legacy_single_country_research.json"
        ).read_text(encoding="utf-8")
    )
    assert "country_isos" not in payload["plan"]
    receipt = research_from_dict(payload)
    assert receipt.plan.country_iso == "UA" and receipt.plan.country_isos == ("UA",)
    restored = replace(version, research=receipt)
    # Pinned legacy shape, before the redundant plural field was introduced.
    original_digest = "3ae9cf30f118faf672afaa1e4537a80b6f607a69a40490ae55751738fb453a5d"
    assert export_content_digest(record, restored) == original_digest
    variants = (
        replace(receipt.plan, country_iso="RU", country_isos=("RU",)),
        replace(receipt.plan, country_iso=None, country_isos=("UA", "RU")),
        replace(receipt.plan, country_iso=None, country_isos=("UA", "CN")),
    )
    digests = {
        export_content_digest(record, replace(version, research=replace(receipt, plan=plan)))
        for plan in variants
    }
    assert len(digests) == 3 and original_digest not in digests
    plural = canonical_snapshot(variants[1])
    assert plural["country_iso"] is None and plural["country_isos"] == ("UA", "RU")
    metadata = {"country_iso": "UA", "country_isos": ("UA",)}
    assert canonical_snapshot(metadata) == metadata
