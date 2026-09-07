"""Automatic claim admission and writes remain inside the parent report transaction."""

from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from ase.application.reports import automatic_claim_storage as storage_module
from ase.application.reports.automatic_claim_storage import AutomaticClaimStorage
from ase.application.reports.automatic_claims import PendingAutomaticClaims
from ase.application.reports.claim_batch import build_proposal_batch, claim_body_digest
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.claim_generation import ClaimGenerationReceipt, ClaimGenerationStatus
from ase.domain.errors import Conflict
from report_documents_helpers import document_records
from team_helpers import CONTEXT
from test_claim_batch_service import proposals_for
from test_claim_origin import origin
from test_claim_repository import seed


def pending_for(container, user, version):
    provenance = origin(container.clock.now())
    revisions = build_proposal_batch(
        version, proposals_for(version), provenance, user.id, container.clock.now()
    )
    return PendingAutomaticClaims(
        version.report_id,
        version.id,
        user.id,
        evidence_digest(version),
        claim_body_digest(version),
        ClaimGenerationReceipt(
            ClaimGenerationStatus.COMPLETED,
            tuple(row.id for row in revisions),
            provenance,
        ),
        revisions,
    )


async def test_automatic_claims_do_not_commit_the_parent_transaction(container, user):
    record, version, _ = await seed(container, user)
    pending = pending_for(container, user, version)
    async with container.session_factory() as session:
        r = container.repositories(session)
        access = await container.access_policy(session).context(user, for_update=True)
        storage = AutomaticClaimStorage(r.claims, container._auditor(r))
        admitted = await storage.admit(access, record, version, pending)
        await storage.write(access, record, version, admitted, CONTEXT)
        assert session.in_transaction()
        assert (await r.claims.scope_usage(user.id, None))[0] == 3
        await session.rollback()
    async with container.session_factory() as session:
        assert (await container.repositories(session).claims.scope_usage(user.id, None))[0] == 1


@pytest.mark.parametrize("quota", ["count", "bytes"])
async def test_capacity_race_becomes_explicit_empty_batch(container, user, monkeypatch, quota):
    record, version, _ = await seed(container, user)
    pending = pending_for(container, user, version)
    monkeypatch.setattr(
        storage_module, "MAX_SCOPE_CLAIMS" if quota == "count" else "MAX_SCOPE_BYTES", 2
    )
    async with container.session_factory() as session:
        r = container.repositories(session)
        access = await container.access_policy(session).context(user, for_update=True)
        storage = AutomaticClaimStorage(r.claims, container._auditor(r))
        admitted = await storage.admit(access, record, version, pending)
        assert admitted.receipt.status is ClaimGenerationStatus.QUOTA_EXCEEDED
        assert admitted.receipt.model_origin == pending.receipt.model_origin
        assert admitted.revisions == ()
        await storage.write(access, record, version, admitted, CONTEXT)
        await session.commit()
        assert (await r.claims.scope_usage(user.id, None))[0] == 1


async def test_second_write_failure_remains_rollbackable(container, user, monkeypatch):
    record, version, _ = await seed(container, user)
    pending = pending_for(container, user, version)
    async with container.session_factory() as session:
        r = container.repositories(session)
        access = await container.access_policy(session).context(user, for_update=True)
        storage = AutomaticClaimStorage(r.claims, container._auditor(r))
        original = r.claims.create
        called = 0

        async def fail_second(*args):
            nonlocal called
            called += 1
            if called == 2:
                raise RuntimeError("Simulated claim storage failure")
            return await original(*args)

        monkeypatch.setattr(r.claims, "create", AsyncMock(side_effect=fail_second))
        admitted = await storage.admit(access, record, version, pending)
        with pytest.raises(RuntimeError):
            await storage.write(access, record, version, admitted, CONTEXT)
        await session.rollback()
        assert (await r.claims.scope_usage(user.id, None))[0] == 1


async def test_changed_pending_anchor_rejected_before_write(container, user):
    record, version, _ = await seed(container, user)
    pending = replace(pending_for(container, user, version), body_sha256="0" * 64)
    async with container.session_factory() as session:
        r = container.repositories(session)
        access = await container.access_policy(session).context(user, for_update=True)
        storage = AutomaticClaimStorage(r.claims, container._auditor(r))
        with pytest.raises(Conflict):
            await storage.admit(access, record, version, pending)
        assert (await r.claims.scope_usage(user.id, None))[0] == 1


async def test_new_report_and_first_claim_rollback_when_second_claim_fails(
    container, user, monkeypatch
):
    record, version = document_records(user.id)
    pending = pending_for(container, user, version)
    async with container.session_factory() as session:
        r = container.repositories(session)
        access = await container.access_policy(session).context(user, for_update=True)
        storage = AutomaticClaimStorage(r.claims, container._auditor(r))
        admitted = await storage.admit(access, record, version, pending)
        await r.reports.add(record, version)
        original = r.claims.create
        calls = 0

        async def fail_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("Simulated second-claim failure")
            return await original(*args)

        monkeypatch.setattr(r.claims, "create", AsyncMock(side_effect=fail_second))
        with pytest.raises(RuntimeError):
            await storage.write(access, record, version, admitted, CONTEXT)
        await session.rollback()
    async with container.session_factory() as session:
        r = container.repositories(session)
        assert await r.reports.get(record.id) is None
        assert await r.reports.get_version(record.id, 1) is None
        assert await r.claims.scope_usage(user.id, None) == (0, 0)


async def test_admin_regeneration_uses_personal_report_owners_quota(
    container, user, admin, monkeypatch
):
    record, version, _ = await seed(container, user)
    pending = pending_for(container, admin, version)
    monkeypatch.setattr(storage_module, "MAX_SCOPE_CLAIMS", 2)
    async with container.session_factory() as session:
        r = container.repositories(session)
        access = await container.access_policy(session).context(admin, for_update=True)
        storage = AutomaticClaimStorage(r.claims, container._auditor(r))
        admitted = await storage.admit(access, record, version, pending)
        assert admitted.receipt.status is ClaimGenerationStatus.QUOTA_EXCEEDED
        assert admitted.revisions == ()
        assert await r.claims.scope_usage(admin.id, None) == (0, 0)
