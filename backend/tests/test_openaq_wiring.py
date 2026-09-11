"""Source admission, private research wiring and frozen OpenAQ export provenance."""

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import replace

from ase.application.reports.markdown_annex import annex_lines
from ase.application.research.source_admission import ControlledResearchProvider
from ase.container.research import research_service
from ase.container.research_sources import research_source_specs
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.report_records import evidence_from_list, evidence_to_list
from ase.domain.research import CollectionStatus
from ase.infrastructure.settings import Settings
from hazard_area_helpers import QUERY
from openaq_helpers import KEY, OpenAqFeed
from research_feed_helpers import CLOCK

SOURCE_ID = "research-openaq-area"


class Admission:
    def __init__(self, active):
        self.active = active

    async def enabled(self, source_id):
        assert source_id == SOURCE_ID
        return self.active

    @asynccontextmanager
    async def guard(self):
        yield


async def test_shared_source_instance_selection_catalogue_and_no_preview_requests(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    service = research_service(feed.http, CLOCK, openaq_api_key=KEY)
    query = replace(QUERY, source_ids=(SOURCE_ID,))
    plan = service.plan(query)
    selected = [task for task in plan.tasks if task.selected]
    assert len(selected) == 1 and selected[0].source_id == SOURCE_ID and selected[0].supported
    assert "11 HTTP requests" in selected[0].spatial_scope
    assert not feed.requests
    provider = next(p for p in service._providers(query) if p.id == SOURCE_ID)
    assert next(p for p in service._providers(query) if p.id == SOURCE_ID) is provider
    assert SOURCE_ID not in {p.id for p in service._challenge_providers(query)}
    provider._client._timer = lambda: feed.time
    provider._client._sleep = feed.sleep
    result = await service.collect(query)
    assert len(result.items) == 1 and result.attempts[0].source_id == SOURCE_ID
    assert result.items[0].observation.acquired_at < query.until
    spec = next(spec for spec in research_source_specs() if spec.id == SOURCE_ID)
    assert spec.requires_key and spec.rating.provenance_role == "aggregator"
    await feed.http.aclose()


async def test_disabled_source_not_listed_or_collected(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    service = research_service(feed.http, CLOCK, (SOURCE_ID,), openaq_api_key=KEY)
    assert SOURCE_ID not in {task.source_id for task in service.plan(QUERY).tasks}
    assert SOURCE_ID not in {spec.id for spec in research_source_specs((SOURCE_ID,))}
    wrapped = ControlledResearchProvider(feed.provider(), Admission(False))
    assert (await wrapped.collect(QUERY)).attempts[0].status is CollectionStatus.UNAVAILABLE
    assert not feed.requests
    await feed.http.aclose()


async def test_disable_during_request_discards_evidence_at_release(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    admission = Admission(True)
    underlying = feed.provider()
    get = underlying._client.get
    entered, release = asyncio.Event(), asyncio.Event()

    async def pending(path):
        if "/licenses/" in path:
            entered.set()
            await release.wait()
        return await get(path)

    monkeypatch.setattr(underlying._client, "get", pending)
    task = asyncio.create_task(ControlledResearchProvider(underlying, admission).collect(QUERY))
    await asyncio.wait_for(entered.wait(), 2)
    admission.active = False
    release.set()
    result = await asyncio.wait_for(task, 2)
    assert not result.items and result.attempts[0].status is CollectionStatus.UNAVAILABLE
    await feed.http.aclose()


async def test_licence_original_units_dates_and_credit_survive_freezing_and_markdown(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    event = (await feed.provider().collect(QUERY)).items[0]
    frozen = EvidenceItem.from_event(
        "E1", event, CLOCK.now(), source_name="OpenAQ", independence_key="OpenAQ"
    )
    restored = evidence_from_list(json.loads(json.dumps(evidence_to_list((frozen,)))))[0]
    assert restored.summary == event.summary and restored.observation == event.observation
    attributes = {row.key: row.value for row in restored.attributes}
    assert attributes["units"] == "µg/m³" and attributes["licence_1_attribution"] == "Station owner"
    markdown = "\n".join(annex_lines((restored,), quality_of_information((restored,)), ()))
    assert "Station owner" in markdown and "µg/m³" in markdown
    assert "opendatacommons.org/licenses/by/1.0/" in markdown
    assert "owner.example" in markdown and event.observation.acquired_at.isoformat() in markdown
    await feed.http.aclose()


def test_settings_key_is_server_only_and_redacted(monkeypatch):
    monkeypatch.setenv("ASE_OPENAQ_API_KEY", KEY)
    settings = Settings(_env_file=None, env="test")
    assert settings.openaq_api_key.get_secret_value() == KEY
    assert KEY not in repr(settings) and KEY not in settings.model_dump_json()
