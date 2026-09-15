"""Saved source content remains subject to current admission on reuse and release."""

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.application.reports.production_checkpoint import ProductionSnapshot, collection_to_dict
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.container.report_job_gate import ReportJobSourceDisabled, check_sources
from ase.domain.report_records import evidence_to_list
from ase.domain.research import ResearchQuery
from ase.domain.research_records import ResearchReceipt
from ase.domain.web_research import WEB_SOURCE_ID, WebCitation, WebResearchRecord
from feeds_helpers import NOW
from report_documents_helpers import document_records
from report_job_helpers import job
from report_job_snapshot_helpers import fixture_evidence


def host(*disabled):
    admission = SimpleNamespace(
        enabled_many=AsyncMock(side_effect=lambda ids: {key: key not in disabled for key in ids})
    )
    return SimpleNamespace(source_admission=admission)


def checkpoint(*, web=None, evidence=()):
    query = ResearchQuery("What happened?", NOW - timedelta(days=1), NOW)
    receipt = replace(ResearchReceipt.build(query, (), len(evidence)), web_research=web)
    return collection_to_dict(
        ProductionSnapshot(Selection(evidence, 0, len(evidence)), None, receipt, query, Totals())
    )


def saved(*, frozen=(), collection=None):
    return job(
        payload={
            "schema_version": 1,
            "input": {"evidence": evidence_to_list(frozen)},
            "collection": collection,
        }
    )


def completed_web():
    return WebResearchRecord(
        "completed",
        "Search completed with generated context.",
        NOW,
        synthesis="Generated context",
        citations=(WebCitation("https://example.org/report", "Public report", 0, 17),),
        consulted_urls=("https://example.org/report",),
        tool_calls=1,
        request_count=1,
    )


@pytest.mark.parametrize("placement", ["frozen", "collected"])
async def test_disabled_evidence_blocks_saved_content_in_each_storage_boundary(placement):
    evidence = fixture_evidence()
    stored = (
        saved(frozen=(evidence,))
        if placement == "frozen"
        else saved(collection=checkpoint(evidence=(evidence,)))
    )
    container = host(evidence.source_id)
    with pytest.raises(ReportJobSourceDisabled):
        await check_sources(container, stored)
    assert container.source_admission.enabled_many.await_args.args == ((evidence.source_id,),)


async def test_source_checks_cover_both_frozen_and_collected_items_without_duplicates():
    first = replace(fixture_evidence(), source_id="first")
    second = replace(fixture_evidence("E2", "two"), source_id="second")
    stored = saved(frozen=(first,), collection=checkpoint(evidence=(first, second)))
    container = host()
    await check_sources(container, stored)
    identifiers = container.source_admission.enabled_many.await_args.args[0]
    assert set(identifiers) == {"first", "second"} and len(identifiers) == 2


async def test_disabled_baseline_source_blocks_reusing_a_scheduled_comparison():
    _, baseline = document_records()
    blocked = baseline.evidence[0].source_id
    container = host(blocked)
    with pytest.raises(ReportJobSourceDisabled):
        await check_sources(container, saved(), baseline)
    assert blocked in container.source_admission.enabled_many.await_args.args[0]


async def test_disabled_fresh_web_blocks_reusing_saved_synthesis_even_without_evidence():
    stored = saved(collection=checkpoint(web=completed_web()))
    container = host(WEB_SOURCE_ID)
    with pytest.raises(ReportJobSourceDisabled):
        await check_sources(container, stored)
    container.source_admission.enabled_many.assert_awaited_once_with((WEB_SOURCE_ID,))


async def test_fresh_web_rechecks_current_admission_on_every_release():
    stored = saved(collection=checkpoint(web=completed_web()))
    container = host()
    await check_sources(container, stored)
    container.source_admission.enabled_many.side_effect = lambda ids: dict.fromkeys(ids, False)
    with pytest.raises(ReportJobSourceDisabled):
        await check_sources(container, stored)
    assert container.source_admission.enabled_many.await_count == 2


@pytest.mark.parametrize(
    "status", ["unavailable", "unsupported", "failed", "timed_out", "not_collected"]
)
async def test_empty_web_receipt_does_not_block_app_source_research(status):
    web = WebResearchRecord(status, "No generated context was admitted.", NOW)
    evidence = fixture_evidence()
    stored = saved(collection=checkpoint(web=web, evidence=(evidence,)))
    container = host(WEB_SOURCE_ID)
    await check_sources(container, stored)
    container.source_admission.enabled_many.assert_awaited_once_with((evidence.source_id,))


async def test_empty_collection_and_metadata_only_projection_do_not_admit_source_content():
    container = host(WEB_SOURCE_ID)
    await check_sources(container, saved(collection=checkpoint()))
    await check_sources(container, job())
    container.source_admission.enabled_many.assert_not_awaited()
