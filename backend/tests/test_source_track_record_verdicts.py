"""Track records count current human citation verdicts on the latest visible versions."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from citation_verdict_helpers import seed_verdict_report, verdict_payload
from helpers import USER_PASSWORD, bearer, create_user, login_token


def _citations(version, source_id):
    labels = {item.label for item in version.evidence if item.source_id == source_id}
    return sum(
        label in labels
        for row in version.body.key_judgements
        for label in (*row.supporting_evidence, *row.contradicting_evidence)
    )


async def test_track_record_counts_current_verdicts_with_denominators(container, client, user):
    record, version, path = await seed_verdict_report(container, user.id)
    source = version.evidence[0].source_id
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for verdict in ("cannot_tell", "does_not_support"):
        container.clock.advance(timedelta(seconds=1))
        response = await client.post(path, headers=headers, json=verdict_payload(verdict=verdict))
        assert response.status_code == 201
    response = await client.get(f"/api/sources/{source}/track-record", headers=headers)
    assert response.status_code == 200, response.text
    verdicts = response.json()["citation_verdicts"]
    assert verdicts["available"] is True and "human opinions" in verdicts["note"]
    assert verdicts["citations"] == _citations(version, source)
    assert (verdicts["citations_with_verdicts"], verdicts["current_verdicts"]) == (1, 1)
    assert (verdicts["does_not_support"], verdicts["cannot_tell"]) == (1, 0)
    assert verdicts["superseded_verdicts"] == 1 and verdicts["reviewers"] == 1

    other = await create_user(container, email="track-other@example.com", password=USER_PASSWORD)
    foreign = bearer(await login_token(client, other.email, USER_PASSWORD))
    hidden = (await client.get(f"/api/sources/{source}/track-record", headers=foreign)).json()
    assert hidden["citation_verdicts"]["current_verdicts"] == 0
    assert hidden["citation_verdicts"]["citations"] == 0

    async with container.session_factory() as session:
        await container.repositories(session).reports.add_version(
            replace(record, latest_version=2), replace(version, id=uuid4(), number=2)
        )
        await session.commit()
    later = (await client.get(f"/api/sources/{source}/track-record", headers=headers)).json()
    assert later["citation_verdicts"]["current_verdicts"] == 0
    assert later["citation_verdicts"]["citations"] == _citations(version, source)
