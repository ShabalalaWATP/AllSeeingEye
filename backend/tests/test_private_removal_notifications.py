"""Account removal scrubs owned credentials without disclosing or deleting another user's."""

from uuid import uuid4

from ase.adapters.persistence.alert_routing_models import AlertWebhookDestinationRow
from ase.adapters.persistence.notification_digest_models import DigestPreferenceRow
from ase.adapters.persistence.notification_models import (
    NotificationPreferenceRow,
    PrivateFeedTokenRow,
)
from ase.domain.private_removal import RemovalRequest, RemovalScope
from private_removal_helpers import apply, authorise, preview


async def test_account_removes_disabled_private_destinations_feed_hashes_and_preferences(
    container, user, admin
):
    await authorise(container, admin, user, inactive=True)
    now = container.clock.now()
    destination_ids = {}
    async with container.session_factory() as session:
        for owner in (user, admin):
            destination_ids[owner.id] = uuid4()
            session.add_all(
                [
                    AlertWebhookDestinationRow(
                        id=destination_ids[owner.id],
                        created_by=owner.id,
                        team_id=None,
                        name="Private endpoint",
                        url_encrypted="synthetic-private-ciphertext",
                        enabled=False,
                        created_at=now,
                    ),
                    PrivateFeedTokenRow(
                        user_id=owner.id,
                        token_hash=owner.id.hex * 2,
                        security_version=1,
                        created_at=now,
                        include_titles=True,
                    ),
                    NotificationPreferenceRow(
                        user_id=owner.id, email_enabled=False, include_names=True
                    ),
                    DigestPreferenceRow(
                        user_id=owner.id,
                        enabled=False,
                        timezone="Europe/Helsinki",
                        hour=9,
                        cursor_at=now,
                        next_due_at=now,
                    ),
                ]
            )
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    plan = await preview(container, admin, request)
    assert not plan.blockers
    assert "synthetic-private-ciphertext" not in str(plan)
    assert user.id.hex * 2 not in str(plan)
    for table in (
        "private_feed_tokens",
        "notification_preferences",
        "notification_digest_preferences",
        "alert_webhook_destinations",
    ):
        assert plan.counts[table] == 1
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        for model in (PrivateFeedTokenRow, NotificationPreferenceRow, DigestPreferenceRow):
            assert await session.get(model, user.id) is None
            assert await session.get(model, admin.id) is not None
        assert await session.get(AlertWebhookDestinationRow, destination_ids[user.id]) is None
        retained = await session.get(AlertWebhookDestinationRow, destination_ids[admin.id])
        assert retained.url_encrypted == "synthetic-private-ciphertext"
