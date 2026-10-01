"""The administrator scorecard counts human citation verdicts in its window, never a score."""

from datetime import timedelta

from citation_verdict_helpers import seed_verdict_report, verdict_payload
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, login_token

ENDPOINT = "/api/admin/research-quality"


async def test_scorecard_counts_window_verdicts_without_prose(client, container, admin, user):
    _, _, path = await seed_verdict_report(container, user.id)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    note = "Private reviewer reasoning about a named person."
    for payload in (
        verdict_payload(verdict="cannot_tell", note=note),
        verdict_payload(verdict="supports", note=note),
        verdict_payload(label="E2", verdict="does_not_support"),
    ):
        container.clock.advance(timedelta(seconds=1))
        assert (await client.post(path, headers=headers, json=payload)).status_code == 201
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    body = (await client.get(ENDPOINT, headers=admin_headers)).json()
    checks = body["citation_checks"]
    assert checks["available"] is True and "human opinions" in checks["note"]
    assert (checks["in_window"], checks["counted"], checks["bound_reached"]) == (3, 3, False)
    assert (checks["current_verdicts"], checks["superseded_verdicts"]) == (2, 1)
    assert (checks["supports"], checks["does_not_support"], checks["cannot_tell"]) == (1, 1, 0)
    assert checks["citations_with_verdicts"] == 2
    assert note not in str(body) and path.split("/")[3] not in str(body)

    container.clock.advance(timedelta(days=8))
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    later = await client.get(ENDPOINT, headers=admin_headers, params={"window_days": 7})
    assert later.json()["citation_checks"]["in_window"] == 0
