"""Spatial catalogue evidence can be reviewed without inventing contrary searches."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from ase.application.reports.challenge import run_challenge
from ase.application.reports.drafting import Draft
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.domain.research import ResearchMode, ResearchQuery
from production_integration_helpers import production_job
from report_documents_helpers import document_records
from report_helpers import ScriptedGateway, filled_store
from test_report_challenge import plans, reviews
from test_research_area import area


class ChallengeGateway(ScriptedGateway):
    async def complete(self, base_url, api_key, model, request):
        payload = plans() if request.schema_name == "challenge_plan" else reviews()
        self.answers = [json.dumps(payload)]
        return await super().complete(base_url, api_key, model, request)


@pytest.mark.parametrize("review_available", [True, False])
async def test_area_challenge_never_repeats_catalogue_and_retains_evidence_review(
    container, user, review_available
):
    _, version = document_records()
    job = production_job(user, container.cipher)
    selection = Selection(version.evidence, 0, len(version.evidence))
    query = ResearchQuery(
        job.title, job.now - job.window, job.now, mode=ResearchMode.DETAILED, area=area()
    )
    collection, redraft, select = AsyncMock(), AsyncMock(), Mock()
    gateway = ChallengeGateway()
    totals = Totals()

    async def profile_for(role):
        return job.profile if review_available else None

    result = await run_challenge(
        job,
        Draft(body=version.body),
        selection,
        query=query,
        store=filled_store(),
        collection=collection,
        gateway=gateway,
        cipher=container.cipher,
        profile_for=profile_for,
        totals=totals,
        select=select,
        redraft=redraft,
    )
    collection.challenge_many.assert_not_awaited()
    redraft.assert_not_awaited()
    select.assert_not_called()
    assert result.selection is selection and not result.challenge.redrafted
    assert len(result.challenge.searches) == len(version.body.key_judgements)
    for search in result.challenge.searches:
        assert search.status == "unavailable"
        assert search.attempts == () and search.collected_items == 0
        assert "area" in search.explanation and "Model review" in search.explanation
    assert [request.schema_name for request in gateway.requests] == (
        ["challenge_reviews"] if review_available else []
    )
    assert all(
        review.status == ("completed" if review_available else "unavailable")
        for review in result.challenge.reviews
    )
    assert len(totals.usage) == int(review_available)
    assert any("searches or reviews were unavailable" in row.message for row in totals.findings)
