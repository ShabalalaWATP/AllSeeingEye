"""The bell shares immutable acknowledgement decisions with the feedback workflow."""

import pytest

from ase.application.bell.alerts import BellAcknowledgements
from ase.domain.alert_feedback import AlertDisposition
from ase.domain.errors import Conflict
from helpers import USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT
from test_alert_feedback import acknowledge, feedback, seed


@pytest.mark.parametrize("bell_first", [True, False])
async def test_bodyless_bell_acknowledgement_preserves_the_first_feedback(
    client, container, user, bell_first
):
    rule, alert = await seed(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    if not bell_first:
        await acknowledge(container, user, alert, AlertDisposition.USEFUL, "Keep this decision")
    result = await client.post(
        "/api/bell/alerts/acknowledge", headers=headers, json={"alert_ids": [str(alert.id)]}
    )
    assert result.status_code == 200, result.text
    retained = await acknowledge(container, user, alert, AlertDisposition.NOISE, "Replace")
    assert retained.disposition is (None if bell_first else AlertDisposition.USEFUL)
    assert retained.disposition_note == (None if bell_first else "Keep this decision")
    counts = await feedback(container, user, rule)
    assert (counts.useful, counts.noise, counts.duplicate) == (0 if bell_first else 1, 0, 0)


async def test_bell_batch_continues_after_one_concurrent_acknowledgement(container, user):
    _, first = await seed(container, user)
    _, competing = await seed(container, user)
    _, last = await seed(container, user)
    signalled = []

    class Signals:
        async def scope(self, created_by, team_id):
            signalled.append((created_by, team_id))

    async with container.session_factory() as session:
        real = container.acknowledge_alert(session)

        class ConcurrentAcknowledgement:
            async def execute(self, actor, alert_id, context):
                if alert_id == competing.id:
                    raise Conflict("Reload the shared decision.")
                return await real.execute(actor, alert_id, context)

        repositories = container.repositories(session)
        service = BellAcknowledgements(
            repositories.alerts,
            ConcurrentAcknowledgement(),
            container.access_policy(session),
            repositories.uow,
            Signals(),
        )
        result = await service.acknowledge(user, [first.id, competing.id, last.id], CONTEXT)
    assert result.acknowledged == (first.id, last.id)
    assert [(failure.alert_id, failure.message) for failure in result.failed] == [
        (competing.id, "Reload the shared decision.")
    ]
    assert signalled == [(user.id, None)]
    async with container.session_factory() as session:
        repository = container.repositories(session).alerts
        assert (await repository.get(first.id)).acknowledged_at is not None
        assert (await repository.get(last.id)).acknowledged_at is not None
        assert (await repository.get(competing.id)).acknowledged_at is None
