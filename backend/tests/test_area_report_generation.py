"""Composed application generation preserves spatial scope through persistence."""

import json
from dataclasses import replace
from datetime import timedelta

from ase.application.ports.feeds import EventQuery
from ase.application.research.service import ResearchCollectionService
from ase.domain.events import Point
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch
from ase.domain.research_area import ResearchArea
from feeds_helpers import make_event
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, ScriptedGateway, filled_store, good_body
from team_helpers import CONTEXT
from test_map_research_origin import AREA, setup
from test_saved_map_views import revise


class SpatialFixture:
    id = "fixture-spatial"
    name = "Synthetic area records"
    spatial_scope = "Synthetic point observations in the exact requested rectangle."

    def __init__(self):
        self.queries = []

    def supports(self, query):
        return True

    def supports_area(self, query):
        return query.area == ResearchArea(AREA)

    async def collect(self, query):
        self.queries.append(query)
        return ResearchBatch(
            tuple(
                make_event(
                    f"area-{index}",
                    source_id=self.id,
                    title=f"Area records {index}",
                    point=Point(0.5, 50.5),
                    published_at=query.until - timedelta(hours=1),
                )
                for index in range(3)
            ),
            (
                CollectionAttempt(
                    self.id,
                    self.name,
                    CollectionStatus.COMPLETED,
                    3,
                    "Synthetic fixture only; no public source verification.",
                ),
            ),
        )


async def test_application_create_and_regenerate_keep_exact_map_origin(client, container, user):
    parent, claims, view, revision, request = await setup(client, container, user)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    provider = SpatialFixture()
    container.research = ResearchCollectionService(lambda query: [provider])
    container.llm = ScriptedGateway("{}", json.dumps(good_body()))
    container.store.upsert(filled_store().query(EventQuery(limit=100)))
    request = replace(request, research_terms=("area records",))
    async with container.session_factory() as session:
        record, first = await container.generate_report(session).execute(user, request, CONTEXT)
    assert record.id != parent.id and record.scope["map_origin"]["revision_id"] == str(revision.id)
    assert first.research.plan.area.geometry == AREA
    # Private collection rewrites event IDs; assert the retained content and origin.
    assert {item.title for item in first.evidence} == {
        f"Area records {index}" for index in range(3)
    }
    assert {item.source_id for item in first.evidence} == {provider.id}
    assert provider.queries[0].area.geometry == AREA
    # Changing the latest view does not change the origin of a regenerated assessment.
    await revise(container, claims, view, revision)
    container.llm = ScriptedGateway("{}", json.dumps(good_body()))
    async with container.session_factory() as session:
        updated, second = await container.generate_report(session).regenerate(
            user, record.id, CONTEXT
        )
    assert updated.scope["map_origin"] == record.scope["map_origin"]
    assert second.research.plan.area == first.research.plan.area
    assert provider.queries[-1].area.geometry == AREA
