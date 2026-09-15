"""Authorised source corrections preserve exact snapshots and original report exports."""

from dataclasses import replace
from uuid import UUID, uuid4

from sqlalchemy import select

from ase.adapters.persistence.models import ReportVersionRow
from ase.adapters.persistence.source_review_models import (
    SourceReviewHeadRow,
    SourceReviewSnapshotRow,
)
from ase.adapters.persistence.teams import SqlTeamRepository, TeamMembershipRow
from ase.domain.teams import MembershipRole, Team, TeamMembership
from ase.domain.users import Role
from helpers import USER_PASSWORD, bearer, create_user, login_token
from source_projection_helpers import BODY
from source_review_test_helpers import review_payload, seed_reviews


async def test_review_axes_correction_and_frozen_history_leave_original_exports_unchanged(
    app, container, client, user
):
    record, version, path = await seed_reviews(app, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    first = await client.post(path + "/source-reviews", headers=headers, json=review_payload())
    assert first.status_code == 201, first.text
    decision = first.json()
    assert decision["review"]["assessor"] == "reviewer"
    assert decision["review"]["assessor_id"] == str(user.id)
    assert decision["review"]["reviewed_at"] == decision["review"]["recorded_at"]
    credibility = review_payload(
        kind="credibility", reliability=None, expertise_basis=None, credibility=1
    )
    assert (
        await client.post(path + "/source-reviews", headers=headers, json=credibility)
    ).status_code == 201
    authenticity = review_payload(
        kind="authenticity", reliability=None, expertise_basis=None, authenticity="established"
    )
    assert (
        await client.post(path + "/source-reviews", headers=headers, json=authenticity)
    ).status_code == 201
    subjects = {BODY.key_judgements[0].id: "population-statistics"}
    frozen = await client.post(
        path + "/source-assessment-snapshots", headers=headers, json={"subjects": subjects}
    )
    assert frozen.status_code == 201, frozen.text
    original_snapshot = frozen.json()
    assessment = original_snapshot["projection"]["assessments"][0]
    assert (assessment["reliability"], assessment["credibility"]) == ("A", 1)
    assert assessment["authenticity"]["status"] == "established"
    assert len(original_snapshot["decision_ids"]) == 3
    correction = review_payload(
        previous_id=decision["review"]["id"],
        reliability="F",
        expertise_basis=None,
        basis="Further review cannot establish competence for this subject.",
    )
    changed = await client.post(path + "/source-reviews", headers=headers, json=correction)
    assert changed.status_code == 201, changed.text
    assert (
        await client.post(path + "/source-reviews", headers=headers, json=correction)
    ).status_code == 409
    later = await client.post(
        path + "/source-assessment-snapshots", headers=headers, json={"subjects": subjects}
    )
    assert later.status_code == 201, later.text
    assert later.json()["projection"]["assessments"][0]["reliability"] == "F"
    old = await client.get(
        path + f"/source-assessment-snapshots/{original_snapshot['id']}", headers=headers
    )
    assert old.status_code == 200 and old.json() == original_snapshot
    assert old.headers["cache-control"] == "private, no-store"
    query = {key: review_payload()[key] for key in ("label", "judgement_id", "subject", "kind")}
    history = await client.get(path + "/source-reviews", params=query, headers=headers)
    assert history.status_code == 200 and [row["number"] for row in history.json()] == [1, 2]
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(record.id, 1)
        assert saved.markdown == version.markdown and saved.body == version.body
        assert (
            saved.evidence == version.evidence
            and saved.source_assessment == version.source_assessment
        )
        assert saved.source_assessment.projection.assessments[0].reliability.value == "F"


async def test_reliability_reuses_scope_but_credibility_cannot_cross_version(
    app, container, client, user
):
    record, version, path = await seed_reviews(app, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (
        await client.post(path + "/source-reviews", headers=headers, json=review_payload())
    ).status_code == 201
    assert (
        await client.post(
            path + "/source-reviews",
            headers=headers,
            json=review_payload(
                kind="credibility", reliability=None, expertise_basis=None, credibility=1
            ),
        )
    ).status_code == 201
    second = replace(version, id=uuid4(), number=2, source_assessment=None)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add_version(
            replace(record, latest_version=2), second
        )
        await session.commit()
    subjects = {BODY.key_judgements[0].id: "population-statistics"}
    frozen = await client.post(
        path.replace("/versions/1", "/versions/2") + "/source-assessment-snapshots",
        headers=headers,
        json={"subjects": subjects},
    )
    assert frozen.status_code == 201, frozen.text
    assessment = frozen.json()["projection"]["assessments"][0]
    assert (assessment["reliability"], assessment["credibility"]) == ("A", 6)
    mismatch = await client.get(
        path + "/source-assessment-snapshots/" + frozen.json()["id"], headers=headers
    )
    assert mismatch.status_code == 404


async def test_foreign_scope_and_client_assessor_injection_are_rejected(
    app, container, client, user
):
    _, _, path = await seed_reviews(app, container, user)
    other = await create_user(container, email="other-reviewer@example.com", password=USER_PASSWORD)
    foreign_headers = bearer(await login_token(client, other.email, USER_PASSWORD))
    assert (
        await client.post(path + "/source-reviews", headers=foreign_headers, json=review_payload())
    ).status_code == 404
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for change in (
        {"assessor_id": str(other.id)},
        {"recorded_at": "2020-01-01"},
        {"policy_version": "trusted"},
        {"credibility": True},
    ):
        assert (
            await client.post(
                path + "/source-reviews", headers=headers, json=review_payload(**change)
            )
        ).status_code == 422
    for change in (
        {"label": "E999"},
        {"judgement_id": "missing"},
        {"reliability": "A", "expertise_basis": None},
        {"credibility": 1},
    ):
        assert (
            await client.post(
                path + "/source-reviews", headers=headers, json=review_payload(**change)
            )
        ).status_code == 422


async def test_valid_target_review_survives_an_unrelated_invalid_draft_citation(
    app, container, client, user
):
    broken = replace(BODY.key_judgements[0], id="KJ-invalid", supporting_evidence=("E999",))
    _, _, path = await seed_reviews(
        app, container, user, body=replace(BODY, key_judgements=(*BODY.key_judgements, broken))
    )
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (
        await client.post(path + "/source-reviews", headers=headers, json=review_payload())
    ).status_code == 201
    result = await client.post(
        path + "/source-assessment-snapshots",
        headers=headers,
        json={
            "subjects": {row.id: "population-statistics" for row in (*BODY.key_judgements, broken)}
        },
    )
    assert result.status_code == 422


async def test_team_read_write_membership_and_archive_guards(app, container, client, user):
    teammate = await create_user(container, email="team-reader@example.com", password=USER_PASSWORD)
    team_id = uuid4()
    now = container.clock.now()
    async with container.session_factory() as session:
        teams = SqlTeamRepository(session)
        await teams.add(Team(team_id, "Source review team", True, user.id, now, now))
        for actor in (user, teammate):
            await teams.put_membership(
                TeamMembership(team_id, actor.id, MembershipRole.MEMBER, now)
            )
        await session.commit()
    _, _, path = await seed_reviews(app, container, user, team_id=team_id)
    owner_headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    reader_headers = bearer(await login_token(client, teammate.email, USER_PASSWORD))
    assert (
        await client.post(path + "/source-reviews", headers=owner_headers, json=review_payload())
    ).status_code == 201
    assert (
        await client.post(path + "/source-reviews", headers=reader_headers, json=review_payload())
    ).status_code == 403
    query = {key: review_payload()[key] for key in ("label", "judgement_id", "subject", "kind")}
    assert (
        await client.get(path + "/source-reviews", headers=reader_headers, params=query)
    ).status_code == 200
    async with container.session_factory() as session:
        membership = await session.get(TeamMembershipRow, (team_id, teammate.id))
        await session.delete(membership)
        team = await SqlTeamRepository(session).get(team_id)
        team.is_active = False
        await SqlTeamRepository(session).save(team)
        await session.commit()
    assert (
        await client.get(path + "/source-reviews", headers=reader_headers, params=query)
    ).status_code == 404
    assert (
        await client.post(path + "/source-reviews", headers=owner_headers, json=review_payload())
    ).status_code == 403


async def test_report_child_cleanup_does_not_erase_reusable_policy_history(
    app, container, client, user
):
    record, version, path = await seed_reviews(app, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (
        await client.post(path + "/source-reviews", headers=headers, json=review_payload())
    ).status_code == 201
    result = await client.post(
        path + "/source-assessment-snapshots",
        headers=headers,
        json={"subjects": {BODY.key_judgements[0].id: "population-statistics"}},
    )
    assert result.status_code == 201, result.text
    async with container.session_factory() as session:
        await container.repositories(session).reports.delete(record.id)
        await session.commit()
    async with container.session_factory() as session:
        assert await session.get(SourceReviewSnapshotRow, UUID(result.json()["id"])) is None
        assert await session.get(ReportVersionRow, version.id) is None
        assert await session.scalar(select(SourceReviewHeadRow)) is not None


async def test_team_report_owner_cannot_regrade_another_owners_history_but_manager_can(
    app, container, client, user
):
    teammate = await create_user(
        container, email="report-owner@example.com", password=USER_PASSWORD
    )
    manager = await create_user(
        container, email="review-manager@example.com", password=USER_PASSWORD, role=Role.MANAGER
    )
    team_id = uuid4()
    now = container.clock.now()
    async with container.session_factory() as session:
        teams = SqlTeamRepository(session)
        await teams.add(Team(team_id, "Shared reviewer policy", True, user.id, now, now))
        for actor, role in (
            (user, MembershipRole.MEMBER),
            (teammate, MembershipRole.MEMBER),
            (manager, MembershipRole.MANAGER),
        ):
            await teams.put_membership(TeamMembership(team_id, actor.id, role, now))
        await session.commit()
    _, _, first_path = await seed_reviews(app, container, user, team_id=team_id)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    first = await client.post(
        first_path + "/source-reviews", headers=headers, json=review_payload()
    )
    assert first.status_code == 201, first.text
    _, _, second_path = await seed_reviews(app, container, teammate, team_id=team_id)
    correction = review_payload(previous_id=first.json()["review"]["id"], reliability="D")
    headers = bearer(await login_token(client, teammate.email, USER_PASSWORD))
    denied = await client.post(second_path + "/source-reviews", headers=headers, json=correction)
    assert denied.status_code == 403, denied.text
    headers = bearer(await login_token(client, manager.email, USER_PASSWORD))
    applied = await client.post(second_path + "/source-reviews", headers=headers, json=correction)
    assert applied.status_code == 201, applied.text
    assert applied.json()["number"] == 2
    assert applied.json()["scope"]["owner_id"] == str(user.id)
    assert applied.json()["review"]["assessor_id"] == str(manager.id)
