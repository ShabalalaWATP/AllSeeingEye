"""Saved source histories reject tampered indexes and stale revision writers."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from ase.adapters.persistence.source_review_models import SourceReviewRevisionRow
from ase.adapters.persistence.source_reviews import SqlSourceReviewRepository
from ase.application.reports.source_review_projection import review_target
from ase.application.reports.source_reviews import ReportSourceReviews
from ase.domain.source_reviews import SourceReviewScope
from helpers import USER_PASSWORD, bearer, create_user, login_token
from source_projection_helpers import BODY, SUBJECT
from source_review_test_helpers import review_payload, seed_reviews
from test_source_review_policy import decision


async def test_repository_compare_and_set_and_index_integrity(app, container, user):
    _, version, _ = await seed_reviews(app, container, user)
    scope = SourceReviewScope(user.id, None)
    target = review_target(version, "E1", BODY.key_judgements[0].id, SUBJECT)
    first = decision(scope, target)
    async with container.session_factory() as session:
        repository = SqlSourceReviewRepository(session)
        assert await repository.append(first)
        await session.commit()
    second = decision(scope, target, number=2, previous=first.review.id)
    async with container.session_factory() as session:
        repository = SqlSourceReviewRepository(session)
        assert await repository.append(second)
        assert not await repository.append(decision(scope, target))
        assert not await repository.append(
            replace(second, review=replace(second.review, id=str(uuid4())))
        )
        assert await repository.history(SourceReviewScope(uuid4(), None), first.key) == ()
        assert await repository.history(scope, first.key) == (first, second)
        await session.commit()
    async with container.session_factory() as session:
        row = await session.get(SourceReviewRevisionRow, UUID(second.review.id))
        row.created_at += timedelta(seconds=1)
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(ValueError, match="indexes"):
            await SqlSourceReviewRepository(session).history(scope, first.key)


async def test_other_person_cannot_inherit_a_personal_source_grade(app, container, client, user):
    _, _, path = await seed_reviews(app, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (
        await client.post(path + "/source-reviews", headers=headers, json=review_payload())
    ).status_code == 201
    other = await create_user(container, email="another-scope@example.com", password=USER_PASSWORD)
    _, _, other_path = await seed_reviews(app, container, other)
    headers = bearer(await login_token(client, other.email, USER_PASSWORD))
    frozen = await client.post(
        other_path + "/source-assessment-snapshots",
        headers=headers,
        json={"subjects": {BODY.key_judgements[0].id: SUBJECT}},
    )
    assert frozen.status_code == 201, frozen.text
    row = frozen.json()["projection"]["assessments"][0]
    assert (row["reliability"], row["credibility"]) == ("F", 6)
    assert frozen.json()["decision_ids"] == []


async def test_session_expiry_before_commit_rolls_back_the_review(
    app, container, client, user, monkeypatch
):
    _, _, path = await seed_reviews(app, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    original = ReportSourceReviews._audit

    async def expire_after_audit(self, *args, **kwargs):
        await original(self, *args, **kwargs)
        container.clock.advance(timedelta(days=1))

    monkeypatch.setattr(ReportSourceReviews, "_audit", expire_after_audit)
    result = await client.post(path + "/source-reviews", headers=headers, json=review_payload())
    assert result.status_code == 401, result.text
    async with container.session_factory() as session:
        assert await session.scalar(select(SourceReviewRevisionRow)) is None
