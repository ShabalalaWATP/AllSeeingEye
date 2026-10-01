"""The research-quality scorecard is administrator-only, bounded and discloses counts only."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from ase.adapters.persistence.models import ReportVersionRow
from ase.application.dto import RequestContext
from ase.domain.users import Role
from ase.domain.validation_types import Finding, Severity
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_PASSWORD,
    bearer,
    create_user,
    login_token,
)
from quality_helpers import insert_job
from report_search_helpers import add_profile
from track_record_helpers import add_version, insert_reports

ENDPOINT = "/api/admin/research-quality"
SECRET_TITLE = "Private assessment of a named person"
SECRET_FINDING = "Judgement KJ1 quotes a private detail."
RECEIPT = {"research": {"attempts": [{"status": s} for s in ("completed", "empty", "unavailable")]}}


async def _admin_get(client, params=None):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.get(ENDPOINT, params=params, headers=bearer(token))
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    return response.json()


def _group(groups, key):
    return next(row for row in groups if row["key"] == key)


async def test_only_an_mfa_verified_administrator_may_read_it(client, container, admin, user):
    assert (await client.get(ENDPOINT)).status_code == 401
    manager = await create_user(
        container, email="manager@example.com", password=USER_PASSWORD, role=Role.MANAGER
    )
    for account in (user, manager):
        token = await login_token(client, account.email, USER_PASSWORD)
        assert (await client.get(ENDPOINT, headers=bearer(token))).status_code == 403
    async with container.session_factory() as session:
        repos = container.repositories(session)
        context = RequestContext(ip="test", user_agent="quality-test")
        unverified = await container._sessions(repos).start(admin, context, mfa_verified=False)
        await repos.uow.commit()
    password_only = bearer(unverified.access.token)
    assert (await client.get(ENDPOINT, headers=password_only)).status_code == 401
    await _admin_get(client)


async def test_saved_versions_and_jobs_are_separate_counted_populations(
    client, container, admin, user
):
    now = container.clock.now()
    profile = await _profile(container)
    await insert_reports(
        container,
        user.id,
        2,
        start=now - timedelta(days=5),
        scope={"research_mode": "quick"},
        profile_id=profile,
        analysis=RECEIPT,
        title=SECRET_TITLE,
    )
    (revised,) = await insert_reports(
        container,
        user.id,
        1,
        start=now - timedelta(days=4),
        status="needs_review",
        scope={"research_mode": "detailed"},
        findings=(
            Finding("citation", Severity.WARNING, "KJ1", SECRET_FINDING),
            Finding("citation", Severity.WARNING, "KJ2", SECRET_FINDING),
            Finding("structure", Severity.ERROR, "body", SECRET_FINDING),
        ),
        tokens=(None, None),
    )
    await add_version(container, revised, 2, now - timedelta(days=3), role="supporting")
    await insert_reports(
        container, user.id, 1, start=now - timedelta(days=2), status="failed", template="sitrep"
    )
    await insert_reports(container, user.id, 1, start=now - timedelta(days=200))
    async with container.session_factory() as session:
        first, second = (
            await session.scalars(
                select(ReportVersionRow.id)
                .where(ReportVersionRow.report_id == revised)
                .order_by(ReportVersionRow.number)
            )
        ).all()
    day = now - timedelta(days=1)
    await insert_job(container, user.id, day, status="completed", version_id=second)
    await insert_job(container, user.id, day, status="failed", error="model.timeout")
    await insert_job(container, user.id, day, status="failed", error="model.timeout", template=None)
    await insert_job(container, user.id, day, status="failed", version_id=first, depth=None)
    await insert_job(container, user.id, day, status="queued", model=None)
    await insert_job(container, user.id, now - timedelta(days=200), status="failed")

    body = await _admin_get(client)

    assert body["window_days"] == 90
    versions = body["versions"]
    assert (versions["bound"], versions["in_window"], versions["counted"]) == (1000, 5, 5)
    assert versions["bound_reached"] is False
    overall = versions["overall"]
    assert (overall["versions"], overall["ready"], overall["needs_review"], overall["failed"]) == (
        5,
        3,
        1,
        1,
    )
    citation = _group(overall["findings"], "citation:warning")
    assert (citation["versions"], citation["occurrences"]) == (1, 2)
    receipts = overall["receipts"]
    assert receipts["versions_with_receipts"] == 2 and receipts["versions_without_receipts"] == 3
    assert (receipts["attempts"], receipts["empty"], receipts["unavailable"]) == (6, 2, 2)
    assert receipts["versions_with_empty_or_unavailable"] == 2
    usage = overall["usage"]
    assert (usage["versions_with_usage"], usage["versions_without_usage"]) == (4, 1)
    assert (usage["prompt_tokens"], usage["completion_tokens"]) == (4800, 1200)
    assert usage["prompt_tokens_per_version"] == 1200
    assert _group(versions["by_template"], "intsum")["versions"] == 4
    assert _group(versions["by_template"], "sitrep")["failed"] == 1
    assert _group(versions["by_depth"], "quick")["versions"] == 2
    assert _group(versions["by_depth"], "not_recorded")["versions"] == 1
    connection = _group(versions["by_connection"], str(profile))
    assert connection["label"] == "Offline semantic model" and connection["versions"] == 2
    assert _group(versions["by_connection"], "not_recorded")["versions"] == 3

    jobs = body["jobs"]
    assert (jobs["bound"], jobs["in_window"], jobs["counted"]) == (1000, 5, 5)
    total = jobs["overall"]
    assert (total["jobs"], total["completed"], total["failed"], total["queued"]) == (5, 1, 3, 1)
    assert (total["failed_without_version"], total["failed_with_version"]) == (2, 1)
    assert total["failure_codes"] == [{"code": "model.timeout", "jobs": 2}]
    assert _group(jobs["by_template"], "not_recorded")["jobs"] == 1
    assert _group(jobs["by_depth"], "not_recorded")["failed_with_version"] == 1
    assert _group(jobs["by_model"], "not_recorded")["queued"] == 1
    assert body["citation_checks"]["available"] is True
    assert body["citation_checks"]["in_window"] == 0

    text = str(body)
    for private in (SECRET_TITLE, SECRET_FINDING, str(revised), "Synthetic job title"):
        assert private not in text
    assert not {"score", "percentage", "accuracy", "quality_rate"} & set(_keys(body))


async def test_the_version_bound_and_window_are_explicit(client, container, admin, user):
    now = container.clock.now()
    await insert_reports(container, user.id, 1_003, start=now - timedelta(days=20), others=0)
    body = await _admin_get(client, {"window_days": 30})
    versions = body["versions"]
    assert (versions["in_window"], versions["counted"], versions["bound_reached"]) == (
        1003,
        1000,
        True,
    )
    assert versions["overall"]["versions"] == 1000
    assert body["window_days"] == 30
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    for bad in ("45", "0", "abc"):
        response = await client.get(ENDPOINT, params={"window_days": bad}, headers=bearer(token))
        assert response.status_code == 422, bad
    narrow = await _admin_get(client, {"window_days": 7})
    assert narrow["versions"]["in_window"] == 0 and narrow["versions"]["by_template"] == []


async def test_a_removed_connection_is_labelled_without_guessing(client, container, admin, user):
    await insert_reports(
        container, user.id, 1, start=container.clock.now() - timedelta(days=1), profile_id=uuid4()
    )
    body = await _admin_get(client)
    (row,) = body["versions"]["by_connection"]
    assert row["label"] == "Connection no longer configured"


async def _profile(container):
    async with container.session_factory() as session:
        return (await add_profile(container, session)).id


def _keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)
