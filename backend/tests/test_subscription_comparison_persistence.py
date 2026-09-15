from dataclasses import replace

import pytest

from ase.adapters.persistence.subscription_comparisons import (
    SqlSubscriptionComparisonRepository,
)
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.domain.errors import Conflict
from ase.domain.research_changes import (
    ChangeClassification,
    ComparisonReason,
    ComparisonState,
)
from ase.domain.subscription_comparisons import EditionComparison
from ase.domain.subscription_editions import EditionCoverage, EditionQuality, EditionWorkflow
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records
from test_subscription_editions import _edition, _revision


async def test_immutable_comparison_roundtrip_and_authorised_history_api(
    client, container, user
) -> None:
    schedule, revision = await _revision(container, user)
    previous_record, previous = document_records(user.id)
    current_record, current = document_records(user.id)
    pending = replace(_edition(schedule, revision), baseline_version_id=previous.id)
    async with container.session_factory() as session:
        reports = container.repositories(session).reports
        await reports.add(previous_record, previous)
        await reports.add(current_record, current)
        repository = SqlSubscriptionEditionRepository(session)
        pending = await repository.reserve(pending)
        completed = replace(
            pending,
            workflow=EditionWorkflow.COMPLETED,
            report_quality=EditionQuality.NEEDS_REVIEW,
            coverage=EditionCoverage.COMPLETE_FOR_PLAN,
            report_id=current.report_id,
            version_id=current.id,
            revision=2,
        )
        assert await repository.advance(completed, expected_revision=1) == completed
        comparison = EditionComparison(
            completed.id,
            previous.id,
            current.id,
            ChangeClassification(
                ComparisonState.NO_NEW_RELEVANT_EVIDENCE,
                (ComparisonReason.ADEQUATE_COVERAGE_NO_NEW_EVIDENCE,),
            ),
            completed.updated_at,
        )
        comparisons = SqlSubscriptionComparisonRepository(session)
        assert await comparisons.add(comparison) == comparison
        assert await comparisons.add(comparison) == comparison
        await session.commit()

    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get(f"/api/schedules/{schedule.id}/editions", headers=bearer(token))

    assert response.status_code == 200
    value = response.json()["items"][0]["comparison"]
    assert value["previous_version_id"] == str(previous.id)
    assert value["current_version_id"] == str(current.id)
    assert value["state"] == "no_new_relevant_captured_evidence"
    assert value["summary"].startswith("No new relevant evidence")
    assert "changed_claim_ids" not in value

    altered = replace(
        comparison,
        result=replace(comparison.result, state=ComparisonState.ASSESSMENT_CHANGED),
    )
    async with container.session_factory() as session:
        with pytest.raises(Conflict, match="different immutable"):
            await SqlSubscriptionComparisonRepository(session).add(altered)


async def test_legacy_edition_history_has_no_invented_comparison(container, user) -> None:
    schedule, revision = await _revision(container, user)
    pending = _edition(schedule, revision)
    async with container.session_factory() as session:
        repository = SqlSubscriptionEditionRepository(session)
        await repository.reserve(pending)
        await session.commit()
    async with container.session_factory() as session:
        repository = SqlSubscriptionEditionRepository(session)
        editions = await repository.history(schedule.id)
        comparisons = await SqlSubscriptionComparisonRepository(session).list_for(
            [item.id for item in editions]
        )
    assert comparisons == {}
