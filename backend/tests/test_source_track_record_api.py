"""A source's track record counts only the caller's latest visible saved versions."""

from datetime import timedelta

import pytest

from ase.container.source_track_record import source_track_record
from ase.domain.errors import InvalidRequest
from ase.domain.teams import MembershipRole
from ase.domain.users import Role
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, create_user, login_token
from source_review_test_helpers import review_payload, seed_reviews
from track_record_helpers import SOURCE, add_team, add_version, insert_reports

ENDPOINT = f"/api/sources/{SOURCE}/track-record"


async def _get(client, email, password=USER_PASSWORD, path=ENDPOINT):
    response = await client.get(path, headers=bearer(await login_token(client, email, password)))
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    return response.json()


def _keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _keys(item)}
    return set()


async def test_roles_grades_and_statuses_come_from_each_latest_saved_version(
    client, container, user
):
    start = container.clock.now() - timedelta(days=3)
    await insert_reports(container, user.id, 1, start=start, title="Supporting")
    await insert_reports(
        container,
        user.id,
        1,
        start=start + timedelta(hours=1),
        role="contradicting",
        status="needs_review",
        grade="C4",
        title="Opposing",
    )
    await insert_reports(container, user.id, 1, start=start + timedelta(hours=2), role="elsewhere")
    await insert_reports(container, user.id, 1, start=start + timedelta(hours=3), role="uncited")
    await insert_reports(container, user.id, 1, start=start + timedelta(hours=4), role="absent")
    (revised,) = await insert_reports(
        container, user.id, 1, start=start + timedelta(hours=5), title="Revised"
    )
    await add_version(container, revised, 2, start + timedelta(hours=6), role="absent")

    body = await _get(client, user.email)

    assert body["source_id"] == SOURCE
    assert (body["report_bound"], body["reports_considered"], body["visible_reports"]) == (
        1000,
        6,
        6,
    )
    assert (body["reports_citing"], body["frozen_items"]) == (4, 4)
    assert body["roles"] == {
        "supporting_judgements": 1,
        "contradicting_judgements": 1,
        "items_cited_elsewhere": 1,
        "items_not_cited": 1,
    }
    assert body["reports_by_status"] == {"ready": 3, "needs_review": 1, "failed": 0}
    assert body["judgements_by_status"] == {"ready": 1, "needs_review": 1, "failed": 0}
    assert body["reliability"] == [{"value": "B", "items": 3}, {"value": "C", "items": 1}]
    assert body["credibility"] == [{"value": "2", "items": 3}, {"value": "4", "items": 1}]
    titles = [entry["title"] for entry in body["entries"]]
    assert titles == ["Synthetic report 0", "Synthetic report 0", "Opposing 0", "Supporting 0"]
    opposing = body["entries"][2]
    assert opposing["status"] == "needs_review" and opposing["version_number"] == 1
    assert (opposing["supporting_judgements"], opposing["contradicting_judgements"]) == (0, 1)
    assert opposing["grades"] == ["C4"]
    assert body["entries_total"] == 4
    assert body["citation_verdicts"]["available"] is False
    assert "KAN-114" not in body["citation_verdicts"]["note"]
    assert body["reviews"] == [] and body["reviews_total"] == 0
    forbidden = {"score", "percentage", "rate", "reliability_score", "accuracy"}
    assert not _keys(body) & forbidden


async def test_other_users_and_non_member_teams_are_never_counted(client, container, user):
    other = await create_user(container, email="other@example.com", password=USER_PASSWORD)
    shared = await add_team(container, other, [(other, MembershipRole.MEMBER)])
    member = await add_team(
        container, other, [(other, MembershipRole.MEMBER), (user, MembershipRole.MEMBER)]
    )
    start = container.clock.now() - timedelta(days=1)
    await insert_reports(container, other.id, 3, start=start)
    await insert_reports(container, other.id, 2, start=start, team_id=shared)
    await insert_reports(container, other.id, 1, start=start, team_id=member, status="failed")
    await insert_reports(container, user.id, 1, start=start, role="absent")

    mine = await _get(client, user.email)
    assert (mine["reports_considered"], mine["visible_reports"], mine["reports_citing"]) == (
        2,
        2,
        1,
    )
    assert mine["reports_by_status"] == {"ready": 0, "needs_review": 0, "failed": 1}

    theirs = await _get(client, other.email)
    assert (theirs["reports_considered"], theirs["reports_citing"]) == (6, 6)


async def test_administrators_count_every_report_under_existing_read_access(
    client, container, admin, user
):
    start = container.clock.now() - timedelta(days=1)
    await insert_reports(container, user.id, 2, start=start)
    body = await _get(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert (body["reports_considered"], body["reports_citing"]) == (2, 2)


async def test_scope_applies_before_the_latest_thousand_report_bound(client, container, user):
    other = await create_user(container, email="busy@example.com", password=USER_PASSWORD)
    start = container.clock.now() - timedelta(days=30)
    # The oldest of 1,001 visible reports cites the source and falls outside the bound.
    await insert_reports(container, user.id, 1, start=start, title="Oldest")
    await insert_reports(
        container, user.id, 999, start=start + timedelta(days=1), role="absent", others=0
    )
    await insert_reports(container, user.id, 1, start=start + timedelta(days=2), title="Newest")
    # Newer reports another user owns must not push the caller's reports out of the bound.
    await insert_reports(container, other.id, 50, start=start + timedelta(days=3))

    body = await _get(client, user.email)
    assert (body["reports_considered"], body["visible_reports"]) == (1000, 1001)
    assert body["reports_citing"] == 1
    assert [entry["title"] for entry in body["entries"]] == ["Newest 0"]


async def test_dated_entries_are_bounded_newest_first(client, container, user):
    start = container.clock.now() - timedelta(days=2)
    await insert_reports(container, user.id, 30, start=start)
    body = await _get(client, user.email)
    assert body["reports_citing"] == 30 and body["entries_total"] == 30
    assert len(body["entries"]) == 25
    assert body["entries"][0]["title"] == "Synthetic report 29"
    dates = [entry["saved_at"] for entry in body["entries"]]
    assert dates == sorted(dates, reverse=True)


async def test_sign_in_and_a_bounded_source_identifier_are_required(client, user):
    assert (await client.get(ENDPOINT)).status_code == 401
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for bad in ("bad id", "x" * 121, "quote%22s", "back%5Cslash"):
        response = await client.get(f"/api/sources/{bad}/track-record", headers=headers)
        assert response.status_code == 422, bad
    unknown = await client.get("/api/sources/never-cited/track-record", headers=headers)
    assert unknown.status_code == 200 and unknown.json()["reports_citing"] == 0


async def test_visible_source_reviews_are_listed_without_reviewer_text(
    app, client, container, user
):
    teammate = await create_user(container, email="mate@example.com", password=USER_PASSWORD)
    outsider = await create_user(container, email="out@example.com", password=USER_PASSWORD)
    team = await add_team(
        container, user, [(user, MembershipRole.MEMBER), (teammate, MembershipRole.MEMBER)]
    )
    record, _, path = await seed_reviews(app, container, user, team_id=team)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for changes in (
        {},
        {"kind": "credibility", "reliability": None, "expertise_basis": None, "credibility": 1},
        {
            "kind": "authenticity",
            "reliability": None,
            "expertise_basis": None,
            "authenticity": "established",
        },
    ):
        saved = await client.post(
            path + "/source-reviews", headers=headers, json=review_payload(**changes)
        )
        assert saved.status_code == 201, saved.text

    for email in (user.email, teammate.email):
        body = await _get(client, email)
        assert body["reviews_total"] == 3
        decisions = {(row["kind"], row["decision"]) for row in body["reviews"]}
        assert decisions == {
            ("reliability", "A"),
            ("credibility", "1"),
            ("authenticity", "established"),
        }
        for review in body["reviews"]:
            assert review["report_id"] == str(record.id) and review["team_scoped"] is True
            assert "basis" not in review
        assert "published methodology" not in str(body)

    hidden = await _get(client, outsider.email)
    assert hidden["reviews"] == [] and hidden["reviews_total"] == 0


async def test_promoted_role_does_not_change_personal_scope(client, container, user):
    manager = await create_user(
        container, email="manager@example.com", password=USER_PASSWORD, role=Role.MANAGER
    )
    await insert_reports(container, user.id, 2, start=container.clock.now() - timedelta(days=1))
    body = await _get(client, manager.email)
    assert body["reports_considered"] == 0 and body["reports_citing"] == 0


async def test_the_service_refuses_identifiers_that_storage_could_escape(container, user):
    async with container.session_factory() as session:
        service = source_track_record(container, session)
        for bad in ("é-source", 'quote"d', "", "-leading"):
            with pytest.raises(InvalidRequest):
                await service.read(user, bad)
