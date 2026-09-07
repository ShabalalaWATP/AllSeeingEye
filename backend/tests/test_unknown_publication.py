"""Unknown publication dates remain absent through live and frozen consumers."""

import io
import json
import zipfile
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from ase.adapters.reports.evidence_package import FrozenEvidencePackageRenderer
from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_events import EventOut
from ase.application.feeds.pipeline import Normaliser
from ase.application.reports.archiving import archive_evidence
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import template_for
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.grading import _has_context
from ase.domain.report_records import evidence_from_list, evidence_to_list
from ase.domain.research import ResearchFocus
from ase.domain.research_context import build_research_context
from ase.domain.research_context_records import context_from_dict, context_to_dict
from ase.domain.story_clustering import build_stories
from ase.domain.trackers import activity, latest_event, timeline, top_event
from feeds_helpers import NOW, make_event
from report_documents_helpers import document_records


def undated():
    return make_event("unknown").with_changes(published_at=None)


def frozen(event):
    return EvidenceItem.from_event("E1", event, NOW, source_name="Fixture", independence_key="")


def test_unknown_dates_survive_normalisation_serialisation_and_export():
    event = Normaliser().process([undated().with_changes(content_hash="")])[0]
    assert event.published_at is None and event.content_hash
    assert EventOut.from_event(event).published_at is None
    item = frozen(event)
    rows = evidence_to_list((item,))
    assert rows[0]["published_at"] is None
    assert evidence_from_list(json.loads(json.dumps(rows))) == (item,)
    context = build_research_context((item,))
    assert context_from_dict(context_to_dict(context)) == context
    assert context.timeline[0].published_at is None
    quality = quality_of_information((item,))
    assert quality.oldest is quality.newest is None
    record, version = document_records()
    with zipfile.ZipFile(
        io.BytesIO(
            FrozenEvidencePackageRenderer().render(
                record,
                replace(version, evidence=(item,)),
            )
        )
    ) as archive:
        assert json.loads(archive.read("evidence.json"))[0]["published_at"] is None
        feature = json.loads(archive.read("evidence.geojson"))["features"][0]
        assert feature["properties"]["published_at"] is None


def test_unknown_dates_do_not_supply_activity_or_temporal_context():
    event = undated()
    dated = make_event("dated")
    assert activity([event], NOW).last_24h == 0
    assert all(bucket.count == 0 for bucket in timeline([event], NOW))
    assert latest_event([event]) is None
    assert latest_event([event, dated]) == dated
    assert top_event([event, dated]) == dated
    assert len(build_stories([event, dated])) == 2
    assert _has_context(event, [dated]) == _has_context(dated, [event]) == 0
    unknown = frozen(event)
    known = replace(frozen(dated), label="E2")
    assert quality_of_information((unknown, known)).newest == dated.published_at
    assert [row.evidence_label for row in build_research_context((unknown, known)).timeline] == [
        "E2",
        "E1",
    ]


def test_explicit_private_input_can_be_selected_without_inventing_a_date():
    event = undated()
    store = InMemoryEventStore()
    store.upsert((event,))
    job = SimpleNamespace(
        request=ReportRequest("ask", research_focus=ResearchFocus.DOCUMENT),
        window=timedelta(days=1),
        template=template_for("ask"),
        now=NOW,
        bbox=None,
        countries=(),
        hazard=None,
        terms=(),
        reused_evidence=(),
        seed_events=(event,),
    )
    result = select_for_job(store, {}, job, None)
    assert len(result.items) == 1 and result.items[0].published_at is None
    job.request = ReportRequest("ask")
    assert select_for_job(store, {}, job, None).items == ()


async def test_unknown_publication_does_not_trigger_automatic_archive():
    record, version = document_records()
    version = replace(
        version, evidence=tuple(replace(item, published_at=None) for item in version.evidence)
    )
    reports = AsyncMock()
    reports.get.return_value = record
    archiver = AsyncMock()
    assert await archive_evidence(archiver, reports, AsyncMock(), version) == 0
    archiver.archive.assert_not_awaited()
