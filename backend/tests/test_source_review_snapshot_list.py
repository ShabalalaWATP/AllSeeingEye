"""Reviewed source snapshots are listed per exact version, and the history cap is explicit."""

from dataclasses import replace
from uuid import uuid4

import ase.application.reports.source_reviews as service
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.domain.teams import MembershipRole
from citation_verdict_helpers import make_team
from helpers import USER_PASSWORD, bearer, create_user, login_token
from source_projection_helpers import BODY
from source_review_test_helpers import review_payload, seed_reviews

SUBJECTS = {BODY.key_judgements[0].id: "population-statistics"}


async def test_snapshots_are_listed_for_their_exact_version_only(app, container, client, user):
    record, version, path = await seed_reviews(app, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    empty = await client.get(path + "/source-assessment-snapshots", headers=headers)
    assert empty.status_code == 200, empty.text
    assert empty.json() == {"snapshots": [], "limit": 20}
    assert empty.headers["cache-control"] == "private, no-store"
    assert (
        await client.post(path + "/source-reviews", headers=headers, json=review_payload())
    ).status_code == 201
    frozen = await client.post(
        path + "/source-assessment-snapshots", headers=headers, json={"subjects": SUBJECTS}
    )
    assert frozen.status_code == 201, frozen.text
    listed = (await client.get(path + "/source-assessment-snapshots", headers=headers)).json()
    (summary,) = listed["snapshots"]
    assert summary["id"] == frozen.json()["id"] and summary["authored_by"] == str(user.id)
    assert summary["decisions"] == 1 and summary["subjects"] == SUBJECTS
    assert summary["report_version_id"] == str(version.id)

    second = replace(version, id=uuid4(), number=2, source_assessment=None)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add_version(
            replace(record, latest_version=2), second
        )
        await session.commit()
    later = path.replace("/versions/1", "/versions/2") + "/source-assessment-snapshots"
    assert (await client.get(later, headers=headers)).json()["snapshots"] == []

    other = await create_user(container, email="snapshot-other@example.com", password=USER_PASSWORD)
    foreign = bearer(await login_token(client, other.email, USER_PASSWORD))
    response = await client.get(path + "/source-assessment-snapshots", headers=foreign)
    assert response.status_code == 404


async def test_team_snapshot_list_follows_current_membership(app, container, client, user):
    reader = await create_user(
        container, email="snapshot-reader@example.com", password=USER_PASSWORD
    )
    team_id = await make_team(
        container, ((user, MembershipRole.MEMBER), (reader, MembershipRole.MEMBER))
    )
    _, _, path = await seed_reviews(app, container, user, team_id=team_id)
    headers = bearer(await login_token(client, reader.email, USER_PASSWORD))
    assert (
        await client.get(path + "/source-assessment-snapshots", headers=headers)
    ).status_code == 200
    async with container.session_factory() as session:
        await session.delete(await session.get(TeamMembershipRow, (team_id, reader.id)))
        await session.commit()
    assert (
        await client.get(path + "/source-assessment-snapshots", headers=headers)
    ).status_code == 404


async def test_full_history_returns_an_explicit_limit_message(
    app, container, client, user, monkeypatch
):
    monkeypatch.setattr(service, "MAX_SOURCE_REVIEW_HISTORY", 1)
    _, _, path = await seed_reviews(app, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    first = await client.post(path + "/source-reviews", headers=headers, json=review_payload())
    assert first.status_code == 201
    correction = review_payload(previous_id=first.json()["review"]["id"], reliability="B")
    full = await client.post(path + "/source-reviews", headers=headers, json=correction)
    assert full.status_code == 422
    assert "revision limit" in full.json()["error"]["message"]
