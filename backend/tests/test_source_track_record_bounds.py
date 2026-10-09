"""Track record scans filter to relevant reports and versions before their row limits."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from ase.adapters.persistence.citation_verdict_models import CitationVerdictRow
from ase.adapters.persistence.source_track_record import SqlSourceTrackRecordReader
from citation_verdict_helpers import seed_verdict_report
from helpers import USER_PASSWORD, bearer, login_token
from source_review_test_helpers import review_payload, seed_reviews

SOURCE = "statistics-office"


def _verdict(record, version, number, owner, at):
    return CitationVerdictRow(
        id=uuid4(),
        report_id=record.id,
        report_version_id=version.id,
        version_number=number,
        judgement_id="KJ1",
        label="E1",
        relation="supporting",
        verdict="supports",
        note=None,
        owner_id=owner,
        team_id=None,
        reviewer_id=owner,
        recorded_at=at,
    )


async def test_superseded_version_verdicts_cannot_crowd_out_current_ones(container, user):
    record, version, _ = await seed_verdict_report(container, user.id)
    current = replace(version, id=uuid4(), number=2)
    now = container.clock.now()
    async with container.session_factory() as session:
        await container.repositories(session).reports.add_version(
            replace(record, latest_version=2), current
        )
        session.add(_verdict(record, current, 2, user.id, now))
        # Newer verdicts on the superseded version sort ahead of the current one.
        for minutes in range(1, 4):
            session.add(_verdict(record, version, 1, user.id, now + timedelta(minutes=minutes)))
        await session.commit()
        visibility = (await container.access_policy(session).context(user)).visibility
        verdicts = await SqlSourceTrackRecordReader(session).verdicts(
            visibility, frozenset({(record.id, 2)}), 1
        )
    assert [(row.report_id, row.version_number) for row in verdicts] == [(record.id, 2)]


async def test_reviews_of_other_reports_cannot_crowd_out_relevant_ones(
    app, client, container, user
):
    relevant, _, relevant_path = await seed_reviews(app, container, user)
    other, _, other_path = await seed_reviews(app, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    saved = await client.post(
        relevant_path + "/source-reviews", headers=headers, json=review_payload()
    )
    assert saved.status_code == 201, saved.text
    for kind, changes in (
        ("credibility", {"reliability": None, "expertise_basis": None, "credibility": 1}),
        (
            "authenticity",
            {"reliability": None, "expertise_basis": None, "authenticity": "established"},
        ),
    ):
        container.clock.advance(timedelta(minutes=1))
        newer = await client.post(
            other_path + "/source-reviews",
            headers=headers,
            json=review_payload(kind=kind, **changes),
        )
        assert newer.status_code == 201, newer.text

    async with container.session_factory() as session:
        visibility = (await container.access_policy(session).context(user)).visibility
        reader = SqlSourceTrackRecordReader(session)
        reviews = await reader.reviews(visibility, SOURCE, frozenset({relevant.id}), 1)
        assert [review.target.report_id for review in reviews] == [relevant.id]
        assert reviews[0].target.source_id == SOURCE
        # Another source's identifier never matches, even as a substring of the payload.
        assert await reader.reviews(visibility, "statistics", frozenset({relevant.id}), 5) == ()
        both = await reader.reviews(visibility, SOURCE, frozenset({relevant.id, other.id}), 5)
        assert {review.target.report_id for review in both} == {relevant.id, other.id}
