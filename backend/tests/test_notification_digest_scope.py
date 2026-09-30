"""SQL count intervals are half-open and exclude administration inspection."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, update

from ase.adapters.persistence.notification_digest_counts import digest_counts
from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.teams import TeamMembershipRow
from ase.container.notifications import digest_preferences, digest_worker
from ase.domain.access import Visibility
from ase.domain.notification_digest import DigestPreferences
from test_notification_delivery import Sender
from test_notification_digest import _enable, _rows
from test_notification_scope import _team
from test_private_feed import _alert


async def _reviews(*_args):
    return 0, False


async def test_count_boundaries_and_terminal_job_statuses(container, user, admin):
    now = container.clock.now()
    await _alert(container, user)
    await _alert(container, admin)
    async with container.session_factory() as session:
        for status in ("completed", "needs_review", "failed", "queued"):
            session.add(
                ReportJobRow(
                    id=uuid4(),
                    request_key=uuid4(),
                    owner_id=user.id,
                    team_id=None,
                    title="SECRET title",
                    status=status,
                    stage="test",
                    created_at=now,
                    updated_at=now,
                    revision=1,
                    payload="{}",
                    payload_sha256="a" * 64,
                    payload_bytes=2,
                    report_id=uuid4(),
                    version_id=uuid4(),
                )
            )
        await session.commit()
        scope = Visibility(user.id, False, ())
        excluded = await digest_counts(session, scope, now - timedelta(days=1), now, _reviews)
        assert excluded.empty
        counted = await digest_counts(session, scope, now, now + timedelta(days=1), _reviews)
        assert (counted.alerts, counted.finished, counted.failed) == (1, 2, 1)
        # Administrator delivery explicitly uses member visibility, not inspection.
        own = await digest_counts(
            session, Visibility(admin.id, False, ()), now, now + timedelta(days=1), _reviews
        )
        assert (own.alerts, own.finished, own.failed) == (1, 0, 0)


async def test_membership_revoked_after_enqueue_removes_digest_content(container, user):
    await _enable(container, user)
    team = await _team(container, user)
    await _alert(container, user)
    async with container.session_factory() as session:
        await session.execute(update(AlertRow).values(team_id=team))
        await session.commit()
    container.clock.advance(timedelta(days=1))
    worker = digest_worker(container)
    await worker._store.enqueue_due(container.clock.now())
    async with container.session_factory() as session:
        await session.execute(delete(TeamMembershipRow).where(TeamMembershipRow.team_id == team))
        await session.commit()
    sender = Sender()
    worker._dispatcher._sender = sender
    await worker._dispatcher.tick()
    assert not sender.messages
    assert (await _rows(container))[0].state == "empty"


async def test_optout_and_reenable_never_revives_old_pending_digest(container, user):
    await _enable(container, user)
    await _alert(container, user)
    container.clock.advance(timedelta(days=1))
    worker = digest_worker(container)
    await worker._store.enqueue_due(container.clock.now())
    async with container.session_factory() as session:
        await digest_preferences(container, session).save(user, DigestPreferences(False))
    async with container.session_factory() as session:
        await digest_preferences(container, session).save(user, DigestPreferences(True))
    assert (await _rows(container))[0].state == "cancelled"
    assert await worker._dispatcher.tick() == 0
