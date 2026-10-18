"""A real SQLite backup/restore plus manual, guarded reconciliation, without live services."""

from datetime import timedelta

import pytest

from ase.adapters.persistence.models import ReportRow, UserRow
from ase.adapters.persistence.private_review_models import PrivateDataReviewRow
from ase.adapters.security.recovery_schema import Restriction
from ase.container import Container
from ase.domain.errors import Conflict, InvalidCredentials, NotFound
from ase.domain.private_removal import RemovalRequest, RemovalScope, ReviewDecision, ReviewPurpose
from ase.domain.users import Role
from backup_helpers import backup, restore
from helpers import ADMIN_PASSWORD, USER_PASSWORD, create_user
from private_removal_helpers import preview, report
from pytest_support import create_schema
from recovery_helpers import journal as journal  # noqa: PLC0414
from team_helpers import CONTEXT, team_service


async def decide(container, admin, owner, decision, journal, revision=0):
    async with container.session_factory() as session:
        return await container.private_removal(session, journal).review(
            admin,
            owner.id,
            decision,
            ReviewPurpose.RIGHTS_REQUEST,
            revision,
        )


async def deactivate(container, admin, owner):
    async with container.session_factory() as session:
        return await container.update_user(session).execute(admin, owner.id, None, False, CONTEXT)


async def remove(container, admin, request, journal):
    plan = await preview(container, admin, request)
    async with container.session_factory() as session:
        return await container.private_removal(session, journal).apply(
            admin, request, plan.fingerprint
        )


async def test_restore_reapplies_later_removal_and_objection_preserving_holds(
    settings,
    clock,
    tmp_path,
    journal,
):
    root = tmp_path / "original"
    root.mkdir()
    (root / ".env.example").write_text("ASE_ENV=test\n")
    (root / "docker-compose.yml").write_text("services: {}\n")
    source = Container(
        settings.model_copy(
            update={
                "database_url": f"sqlite+aiosqlite:///{root / 'source.db'}",
            }
        ),
        clock=clock,
    )
    try:
        await create_schema(source.engine, fresh=True)
        admin = await create_user(
            source, email="admin@example.com", password=ADMIN_PASSWORD, role=Role.ADMIN
        )
        erased = await create_user(source, email="erased@example.com", password=USER_PASSWORD)
        held = await create_user(source, email="held@example.com", password=USER_PASSWORD)
        authorised = await create_user(
            source, email="permission@example.com", password=USER_PASSWORD
        )
        erased_report, _ = await report(source, erased)
        held_report, _ = await report(source, held)
        permission_report, _ = await report(source, authorised)
        async with team_service(source) as teams:
            team = await teams.create(admin, "Shared retained research", CONTEXT)
        shared, _ = await report(source, erased, team_id=team.id)
        bundle = tmp_path / "old-backup"
        assert (
            backup.main(
                [
                    "sqlite",
                    "--database",
                    str(root / "source.db"),
                    "--output",
                    str(bundle),
                    "--project-root",
                    str(root),
                ]
            )
            == 0
        )
        assert not list(bundle.rglob("*.fernet"))
        # These actions happen AFTER the recovery point, in the independently protected journal.
        await deactivate(source, admin, erased)
        await decide(source, admin, erased, ReviewDecision.REMOVE, journal)
        request = RemovalRequest(erased.id, RemovalScope.ACCOUNT)
        await remove(source, admin, request, journal)
        await decide(source, admin, authorised, ReviewDecision.REMOVE, journal)
        await decide(source, admin, held, ReviewDecision.HOLD, journal)
        journal.record(
            admin.id,
            Restriction(
                owner=held.id,
                restriction="objection",
                purpose=ReviewPurpose.RIGHTS_REQUEST,
                due=clock.now() + timedelta(days=90),
            ),
            clock.now(),
        )
    finally:
        await source.dispose()

    recovered_path = tmp_path / "recovered"
    assert restore.main([str(bundle), "--output", str(recovered_path)]) == 0
    recovered = Container(
        settings.model_copy(
            update={
                "database_url": f"sqlite+aiosqlite:///{recovered_path / 'database.sqlite3'}",
            }
        ),
        clock=clock,
    )
    try:
        # No workers, listener or outbound mailer run. Inspect all history, not timestamps.
        history = journal.inspect()
        removals = [
            e
            for e in history["events"]
            if e["action"]["kind"] == "removal" and e["status"] == "committed"
        ]
        assert len(removals) == 1 and removals[0]["action"]["owner"] == str(erased.id)
        assert history["activation_authorised"] is False
        async with recovered.session_factory() as session:
            assert (await session.get(UserRow, erased.id)).is_active
            assert await session.get(ReportRow, erased_report.id) is not None
        # Manual checklist: reapply objections and current holds first through normal guards.
        await deactivate(recovered, admin, held)
        await decide(recovered, admin, held, ReviewDecision.HOLD, journal)
        await deactivate(recovered, admin, erased)
        await decide(recovered, admin, erased, ReviewDecision.REMOVE, journal)
        await remove(recovered, admin, request, journal)
        with pytest.raises(Conflict, match="preservation_hold"):
            await remove(
                recovered,
                admin,
                RemovalRequest(held.id, RemovalScope.REPORT, held_report.id),
                journal,
            )
        # Permission-only does not delete. Repeated account removal stops at the tombstone.
        with pytest.raises(Conflict, match="account_already_removed"):
            await remove(recovered, admin, request, journal)
        # Ownership drift is not treated as an absent/already-reconciled target.
        with pytest.raises(NotFound):
            await preview(
                recovered, admin, RemovalRequest(erased.id, RemovalScope.REPORT, held_report.id)
            )
        async with recovered.session_factory() as session:
            identity = await session.get(UserRow, erased.id)
            assert not identity.is_active and identity.password_hash is None
            assert identity.security_version > erased.security_version
            assert (await session.get(PrivateDataReviewRow, erased.id)).erased_at is not None
            assert await session.get(ReportRow, erased_report.id) is None
            for preserved in (held_report, permission_report, shared):
                assert await session.get(ReportRow, preserved.id) is not None
        for owner in (erased, held):
            async with recovered.session_factory() as session:
                with pytest.raises(InvalidCredentials):
                    await recovered.login(session).execute(owner.email, USER_PASSWORD, CONTEXT)
        assert journal.inspect()["unresolved_intents"] == []
    finally:
        await recovered.dispose()
