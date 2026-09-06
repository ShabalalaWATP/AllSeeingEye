"""Area research uses an authorised exact map revision, never implicit parent evidence."""

import json
from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import update

from ase.adapters.persistence.map_view_models import MapViewRevisionRow
from ase.application.ports.feeds import EventQuery
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.map_origin import ReportMapOrigin
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import template_for
from ase.container.research import private_research_store
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.map_geometry import parse_map_geometry
from ase.domain.map_research_origin import origin_from_dict, origin_to_dict
from ase.domain.research import ResearchBatch, ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_area import ResearchArea
from feeds_helpers import NOW
from report_helpers import filled_store
from team_helpers import CONTEXT, team_service
from test_report_team_scope import save_team_report, team_for
from test_saved_map_views import STATE, claims_for, create, revise

AREA = parse_map_geometry(
    json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 50], [1, 50], [1, 51], [0, 51], [0, 50]]],
                    },
                }
            ],
        }
    )
)


async def setup(client, container, user, team_id=None):
    parent = await save_team_report(container, user, team_id)
    claims = await claims_for(client, container, user)
    view, revision = await create(container, claims, parent.id, replace(STATE, aoi=AREA))
    request = ReportRequest(
        "ask",
        question="Which records cover this area?",
        research_mode=ResearchMode.QUICK,
        team_id=team_id,
        map_view_id=view.id,
        map_revision_id=revision.id,
        disclose_area_to_provider=True,
    )
    return parent, claims, view, revision, request


def resolver(container, session):
    repos = container.repositories(session)
    return ReportMapOrigin(container.access_policy(session), repos.reports, repos.map_views)


async def test_exact_origin_survives_newer_revision_and_roundtrips_scope(client, container, user):
    parent, claims, view, revision, request = await setup(client, container, user)
    # New revision has no AOI. The old explicit reference must retain its original geometry.
    await revise(container, claims, view, revision)
    async with container.session_factory() as session:
        result = await resolver(container, session).resolve(user, request)
        origin = result.map_origin
        assert origin.revision_id == revision.id and origin.area.geometry == AREA
        assert origin.report_id == parent.id and origin.report_version_number == 1
        assert origin_from_dict(origin_to_dict(origin)) == origin
        scope = report_scope(result, template_for("ask"))
        assert ReportRequest.from_scope("ask", scope).map_origin == origin
        assert result.parent_report_id is None and result.research_input_id is None
        assert await resolver(container, session).resolve(user, result) == result


@pytest.mark.parametrize(
    "change",
    [
        {"map_revision_id": None},
        {"map_view_id": None},
        {"disclose_area_to_provider": False},
        {"research_mode": None},
        {"research_focus": ResearchFocus.COMPANY},
        {"parent_report_id": uuid4()},
        {"research_input_id": uuid4()},
        {"plan_id": uuid4()},
        {"country_iso": "GB"},
    ],
)
async def test_ambiguous_or_undisclosed_origin_rejected(client, container, user, change):
    *_, request = await setup(client, container, user)
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest):
            await resolver(container, session).resolve(user, replace(request, **change))


async def test_admin_cannot_copy_other_private_origin_to_own_scope(client, container, user, admin):
    *_, request = await setup(client, container, user)
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="same personal or team scope"):
            await resolver(container, session).resolve(admin, request)
        # Regenerating an existing report retains its original owner's scope.
        resolved = await resolver(container, session).resolve(admin, request, owner_id=user.id)
        assert resolved.map_origin is not None


async def test_team_origin_cannot_become_private(client, container, user, admin):
    team = await team_for(container, admin, user)
    *_, request = await setup(client, container, user, team.id)
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="same personal or team scope"):
            await resolver(container, session).resolve(user, replace(request, team_id=None))


async def test_missing_and_tampered_revisions_fail_closed(client, container, user):
    _, _, _, revision, request = await setup(client, container, user)
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await resolver(container, session).resolve(
                user, replace(request, map_revision_id=uuid4())
            )
        await session.execute(
            update(MapViewRevisionRow)
            .where(MapViewRevisionRow.id == revision.id)
            .values(title="Changed without a revision")
        )
        await session.commit()
        with pytest.raises(Conflict):
            await resolver(container, session).resolve(user, request)


async def test_final_authorisation_rechecks_deleted_origin(client, container, user):
    parent, _, _, _, request = await setup(client, container, user)
    async with container.session_factory() as session:
        request = await resolver(container, session).resolve(user, request)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.reports.delete(parent.id)
        await repos.uow.commit()
    async with container.session_factory() as session:
        repos = container.repositories(session)
        auth = ReportAuthorisation(
            container.access_policy(session),
            repos.reports,
            repos.plans,
            repos.aois,
            repos.uow,
            resolver(container, session),
        )
        with pytest.raises(NotFound):
            await auth.finish(user, request, None, None)


async def test_strict_area_collection_does_not_copy_unrelated_global_context():
    query = ResearchQuery(
        "Records in this area",
        NOW - timedelta(days=1),
        NOW + timedelta(minutes=1),
        area=ResearchArea(AREA),
    )
    request = ReportRequest("ask", research_mode=ResearchMode.QUICK)
    collection = AsyncMock()
    collection.collect.return_value = ResearchBatch()
    live = filled_store()
    assert live.query(EventQuery(limit=100))
    private, receipt = await collect_report_evidence(
        query, request, collection, private_research_store, live
    )
    assert private.query(EventQuery(limit=100)) == []
    assert receipt.collected_items == 0
    assert live.query(EventQuery(limit=100))


async def test_final_authorisation_rechecks_revoked_team_membership(client, container, user, admin):
    team = await team_for(container, admin, user)
    *_, request = await setup(client, container, user, team.id)
    async with container.session_factory() as session:
        request = await resolver(container, session).resolve(user, request)
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        auth = ReportAuthorisation(
            container.access_policy(session),
            repos.reports,
            repos.plans,
            repos.aois,
            repos.uow,
            resolver(container, session),
        )
        with pytest.raises(NotFound):
            await auth.finish(user, request, None, None)
